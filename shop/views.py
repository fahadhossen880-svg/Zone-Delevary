from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import models
from django.http import JsonResponse
from .models import Category, Product, UserProfile, Zone, Order, OrderItem, Notification, HeroSlide, NotificationPreference, AdminNotice
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm, CheckoutForm
from .recommendation_engine import get_personalized_products
from .utils import get_google_maps_api_key
from .notification_service import (
    create_notification,
    get_notifications,
    get_unread_count,
    delete_notification,
    clear_all_notifications,
    update_order_notifications,
)
from .firebase_config import (
    set_user_location,
    update_realtime_notification_status,
    push_notification_preferences,
)
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


def home(request):
    # Get hero slides
    try:
        hero_slides = HeroSlide.objects.filter(is_active=True)
    except Exception as e:
        hero_slides = []
    
    try:
        zones = Zone.objects.filter(is_active=True).only('id', 'name', 'description')
    except Exception as e:
        zones = []
    
    try:
        selected_zone = request.GET.get('zone')
        session_id = request.session.session_key

        # Get user location if available
        user_location = None
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            # Try to get location from user profile or recent orders
            recent_order = Order.objects.filter(customer=request.user).order_by('-created_at').first()
            if recent_order and recent_order.latitude and recent_order.longitude:
                user_location = {
                    'lat': recent_order.latitude,
                    'lng': recent_order.longitude
                }

        if selected_zone:
            # If zone is selected, show all products from that zone ordered by category display order
            products = Product.objects.filter(zone_id=selected_zone, is_available=True).select_related('category', 'zone').order_by('category__display_order', 'category__name', '-created_at')
        else:
            # Show all available products on the home page ordered by category display order
            products = Product.objects.filter(is_available=True).select_related('category', 'zone').order_by('category__display_order', 'category__name', '-created_at')
    except Exception as e:
        products = []
    
    try:
        print("DEBUG: Starting category loading...")
        # Get categories ordered by display_order
        categories = Category.objects.all().order_by('display_order', 'name')
        print(f"DEBUG: Found {len(categories)} categories")
        
        # Fix any categories without slugs
        for cat in categories:
            print(f"DEBUG: Checking category '{cat.name}' with slug '{cat.slug}'")
            if not cat.slug and cat.name:
                from django.utils.text import slugify
                base_slug = slugify(cat.name) or 'category'
                slug = base_slug
                counter = 1
                while Category.objects.filter(slug=slug).exclude(pk=cat.pk).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                cat.slug = slug
                cat.save()
                print(f"Fixed category '{cat.name}' with slug '{cat.slug}'")
    except Exception as e:
        print(f"DEBUG: Exception in category loading: {e}")
        categories = []
    
    # Get active notices for marquee display
    try:
        now = timezone.now()
        active_notices = AdminNotice.objects.filter(
            is_active=True,
            is_marquee=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-priority', '-created_at')[:1]  # Get the highest priority active notice
    except Exception as e:
        active_notices = []
    
    context = {
        'hero_slides': hero_slides,
        'categories': categories,
        'products': products,
        'zones': zones,
        'selected_zone': selected_zone if selected_zone else None,
        'active_notices': active_notices,
        'title': 'ZoneDelivery - তোমার জোনের ডেলিভারি'
    }
    return render(request, 'shop/home.html', context)


def product_detail(request, product_id):
    """Display detailed view of a product and track user behavior"""
    try:
        product = get_object_or_404(Product.objects.select_related('category', 'zone'), id=product_id)

        # Track product view
        session_id = request.session.session_key
        from .recommendation_engine import ProductRecommendationEngine
        engine = ProductRecommendationEngine(
            user=request.user if request.user.is_authenticated else None,
            session_id=session_id
        )
        engine.track_product_view(product)

        # Update user preferences
        if request.user.is_authenticated:
            engine.update_user_preferences(
                category=product.category,
                zone=product.zone,
                product=product
            )

        # Get related products (similar category, same zone)
        related_products = Product.objects.filter(
            category=product.category,
            zone=product.zone,
            is_available=True
        ).exclude(id=product.id)[:4]

        context = {
            'product': product,
            'related_products': related_products,
            'title': f'{product.title} - ZoneDelivery'
        }
        return render(request, 'shop/product_detail.html', context)

    except Exception as e:
        messages.error(request, 'প্রোডাক্ট খুঁজে পাওয়া যায়নি।')
        return redirect('home')


def category_detail(request, slug):
    """Display all products for a specific category"""
    try:
        category = get_object_or_404(Category, slug=slug)

        # Track category preference
        if request.user.is_authenticated:
            from .recommendation_engine import ProductRecommendationEngine
            engine = ProductRecommendationEngine(user=request.user)
            engine.update_user_preferences(category=category)
    except Exception as e:
        messages.error(request, 'ক্যাটেগরি খুঁজে পাওয়া যায়নি।')
        return redirect('home')
    
    try:
        zones = Zone.objects.filter(is_active=True).only('id', 'name', 'description')
    except Exception as e:
        zones = []
    
    try:
        selected_zone = request.GET.get('zone')
        if selected_zone:
            products = Product.objects.filter(
                category=category, 
                zone_id=selected_zone, 
                is_available=True
            ).select_related('category', 'zone')
        else:
            products = Product.objects.filter(
                category=category, 
                is_available=True
            ).select_related('category', 'zone')
    except Exception as e:
        products = []
    
    context = {
        'category': category,
        'products': products,
        'zones': zones,
        'selected_zone': selected_zone if selected_zone else None,
        'title': f'{category.name} - ZoneDelivery'
    }
    return render(request, 'shop/category_detail.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে! এখন লগইন করুন।')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegisterForm()
    
    context = {
        'form': form,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
    }
    return render(request, 'shop/register.html', context)


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']
            user = None

            if '@' in identifier:
                user = User.objects.filter(email__iexact=identifier).first()
            else:
                profile = UserProfile.objects.filter(phone__iexact=identifier).select_related('user').first()
                if profile:
                    user = profile.user

            if user is not None:
                user = authenticate(request, username=user.username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'স্বাগতম {user.get_full_name() or user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'ইমেইল/মোবাইল নম্বর বা পাসওয়ার্ড ভুল।')
    else:
        form = UserLoginForm()
    
    context = {
        'form': form,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
    }
    return render(request, 'shop/login.html', context)


def google_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, 'Google login configured করা হয়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।')
        return redirect('login')

    state = str(uuid.uuid4())
    request.session['google_oauth_state'] = state

    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
    return redirect(auth_url)


def google_callback(request):
    if request.user.is_authenticated:
        return redirect('home')

    error = request.GET.get('error')
    if error:
        messages.error(request, 'Google authorization ব্যর্থ হয়েছে।')
        return redirect('login')

    state = request.GET.get('state')
    saved_state = request.session.pop('google_oauth_state', None)
    if not state or state != saved_state:
        messages.error(request, 'অবৈধ Google লগইন সেশন। আবার ট্রাই করুন।')
        return redirect('login')

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google থেকে authorization code পাওয়া যায়নি।')
        return redirect('login')

    try:
        token_data = urllib.parse.urlencode({
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }).encode('utf-8')

        token_request = urllib.request.Request(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urllib.request.urlopen(token_request) as token_response:
            token_result = json.load(token_response)

        access_token = token_result.get('access_token')
        if not access_token:
            raise ValueError('Access token missing from Google response')

        userinfo_request = urllib.request.Request(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        with urllib.request.urlopen(userinfo_request) as userinfo_response:
            userinfo = json.load(userinfo_response)

    except urllib.error.HTTPError as exc:
        messages.error(request, 'Google authorization সার্ভারে সমস্যা হয়েছে।')
        return redirect('login')
    except Exception as exc:
        messages.error(request, 'Google login প্রক্রিয়ায় সমস্যা হয়েছে।')
        return redirect('login')

    email = userinfo.get('email')
    if not email:
        messages.error(request, 'Google থেকে ই-মেইল পাওয়া যায়নি।')
        return redirect('login')

    first_name = userinfo.get('given_name', '')
    last_name = userinfo.get('family_name', '')
    display_name = userinfo.get('name') or email.split('@')[0]

    def get_unique_username(base_name):
        slug = slugify(base_name) or 'user'
        candidate = slug
        counter = 0
        while User.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f'{slug}{counter}'
        return candidate

    username = get_unique_username(display_name)
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'is_active': True,
        }
    )

    if created:
        user.set_unusable_password()
        user.save()
        UserProfile.objects.create(user=user, role='customer')
    else:
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'customer'})

    login(request, user)
    messages.success(request, 'Google দ্বারা সফলভাবে লগইন হয়েছে।')
    return redirect('home')


def user_logout(request):
    logout(request)
    messages.success(request, 'লগআউট করেছেন সফলভাবে।')
    return redirect('home')


@login_required(login_url='login')
def admin_register(request):
    """Admin registration page - Only for existing admins"""
    # Check if user is admin (custom role or superuser)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin')
    if not is_admin:
        messages.error(request, 'আপনার এই পেজ এক্সেস করার অনুমতি নেই।')
        return redirect('home')
    
    if request.method == 'POST':
        from .forms import AdminRegisterForm
        form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Make the new user a admin
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            
            # Create or update UserProfile with admin role
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'admin'
            profile.save()
            
            messages.success(request, f'Admin ইউজার "{user.username}" সফলভাবে তৈরি হয়েছে!')
            return redirect('admin_register')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        from .forms import AdminRegisterForm
        form = AdminRegisterForm()
    
    # Get all admin users (both Django superusers and custom admin role)
    admin_users = User.objects.filter(is_superuser=True).values('username', 'email', 'date_joined')
    
    context = {
        'form': form,
        'admin_users': admin_users,
        'title': 'Admin Registration'
    }
    return render(request, 'shop/admin_register.html', context)


@login_required(login_url='login')
def profile(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, role='customer')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            profile.save()
            messages.success(request, 'প্রোফাইল আপডেট হয়েছে সফলভাবে।')
            return redirect('profile')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)
    
    context = {
        'profile': profile,
        'form': form,
    }
    return render(request, 'shop/profile.html', context)


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).select_related('zone').prefetch_related('items').order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'shop/my_orders.html', context)


@login_required(login_url='login')
def order_detail(request, order_id):
    try:
        # Check user role for access control
        user_role = getattr(request.user.profile, 'role', 'customer') if hasattr(request.user, 'profile') else 'customer'
        
        if user_role == 'admin':
            # Admins can view any order
            order = Order.objects.get(id=order_id)
        elif user_role == 'manager':
            # Managers can view orders in their assigned zone
            if request.user.profile.zone_assigned:
                order = Order.objects.get(
                    id=order_id, 
                    zone=request.user.profile.zone_assigned
                )
            else:
                messages.error(request, 'আপনার কোনো জোন নির্ধারিত হয়নি।')
                return redirect('home')
        elif user_role == 'rider':
            # Riders can view orders assigned to them
            order = Order.objects.get(id=order_id, rider=request.user)
        else:
            # Regular customers can only view their own orders
            order = Order.objects.get(id=order_id, customer=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'অর্ডার পাওয়া যায়নি।')
        return redirect('my_orders')
    
    items = order.items.all()
    total_price = order.total_amount + order.delivery_charge
    
    context = {
        'order': order,
        'items': items,
        'total_price': total_price,
    }
    return render(request, 'shop/order_detail.html', context)


def rider_dashboard(request):
    """রাইডারদের জন্য Management Panel"""
    from django.utils import timezone
    
    # Rider check
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'rider':
        messages.error(request, 'আপনি রাইডার নন।')
        return redirect('home')
    
    # Handle POST requests (order accept/status update)
    if request.method == 'POST':
        action = request.POST.get('action')
        order_id = request.POST.get('order_id')
        
        try:
            if action == 'accept':
                # Rider accepts an order - Use select_for_update to prevent race conditions
                from django.db import transaction
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    # BUG FIX #2 & #8: Check both rider is None AND status is 'approved'
                    if order.rider is None and order.status == 'approved':
                        order.rider = request.user
                        order.status = 'confirmed'
                        order.save()
                        # Create notifications
                        update_order_notifications(order, 'confirmed')
                        messages.success(request, f'অর্ডার #{order.order_id} গ্রহণ করা হয়েছে।')
                    elif order.rider is not None:
                        messages.error(request, 'এই অর্ডার ইতিমধ্যে নিয়োগ করা হয়েছে।')
                    else:
                        messages.error(request, 'এই অর্ডারটি আর উপলব্ধ নয়।')
            
            elif action == 'update_status':
                # BUG FIX #3: Check rider authorization BEFORE fetching order
                order = Order.objects.select_for_update().get(id=order_id, rider=request.user)
                status = request.POST.get('status')
                # Validate status is valid choice
                valid_statuses = dict(Order._meta.get_field('status').choices).keys()
                if status in valid_statuses:
                    order.status = status
                    order.save()
                    # Create notifications for status change
                    update_order_notifications(order, status)
                    
                    status_text = 'পিক আপ' if status == 'picked' else 'ডেলিভারি সম্পন্ন'
                    messages.success(request, f'অর্ডার #{order.order_id} {status_text} চিহ্নিত করা হয়েছে।')
                else:
                    messages.error(request, 'অবৈধ স্ট্যাটাস।')
        except Order.DoesNotExist:
            messages.error(request, 'অনুমতি নেই বা অর্ডার পাওয়া যায়নি।')
    
    # Get data for dashboard
    # BUG FIX #8: Show 'approved' orders (manager approved, awaiting rider) not 'pending' (awaiting manager)
    pending_orders = Order.objects.filter(
        status='approved', 
        rider__isnull=True
    ).select_related('customer', 'zone')
    
    # Active deliveries for this rider (confirmed or picked)
    active_deliveries = Order.objects.filter(
        rider=request.user,
        status__in=['confirmed', 'picked']
    ).select_related('customer', 'zone').prefetch_related('items')
    
    # Completed deliveries
    completed_orders = Order.objects.filter(
        rider=request.user,
        status='delivered'
    ).select_related('customer', 'zone').order_by('-created_at')
    
    # Stats
    completed_count = completed_orders.count()
    total_earnings = completed_orders.aggregate(
        total=models.Sum('delivery_charge')
    )['total'] or 0
    
    context = {
        'pending_orders': pending_orders,
        'active_deliveries': active_deliveries,
        'completed_orders': completed_orders,
        'completed_count': completed_count,
        'total_earnings': total_earnings,
        'today': timezone.now(),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,  # BUG FIX #1: Add Google Maps API key
    }
    return render(request, 'shop/rider_dashboard.html', context)


# ============ RIDER ORDER DETAIL ============
@login_required(login_url='login')
def rider_order_detail(request, order_id):
    """Rider can view order details with customer location map"""
    # Check if user is a rider
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'rider':
        messages.error(request, 'আপনি রাইডার নন।')
        return redirect('home')
    
    # Get the order
    order = get_object_or_404(Order, id=order_id)
    
    # Check if rider has access to this order
    if order.rider != request.user:
        messages.error(request, 'আপনার কাছে এই অর্ডার দেখার অনুমতি নেই।')
        return redirect('rider_dashboard')
    
    # Get order items
    items = order.items.all()
    
    # Handle status update
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Order._meta.get_field('status').choices):
            order.status = status
            order.save()
            # Create notifications for status change
            update_order_notifications(order, status)
            status_text = 'পিক আপ' if status == 'picked' else 'ডেলিভারি সম্পন্ন'
            messages.success(request, f'অর্ডার #{order.order_id} {status_text} চিহ্নিত করা হয়েছে।')
            return redirect('rider_order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'items': items,
        'status_choices': Order._meta.get_field('status').choices,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,  # BUG FIX #1: Add Google Maps API key
    }
    return render(request, 'shop/rider_order_detail.html', context)


@login_required(login_url='login')
def rider_return_delivery(request, order_id):
    """Rider requests to return a delivery"""
    # Check if user is a rider
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'rider':
        messages.error(request, 'আপনি রাইডার নন।')
        return redirect('home')
    
    # Get the order
    order = get_object_or_404(Order, id=order_id)
    
    # Check if rider has access to this order
    if order.rider != request.user:
        messages.error(request, 'আপনার কাছে এই অর্ডার দেখার অনুমতি নেই।')
        return redirect('rider_dashboard')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'কোনো কারণ দেওয়া হয়নি')
        
        # Update order status to return_requested
        order.status = 'return_requested'
        order.save()
        
        # BUG FIX #5: Check if manager exists before creating notification
        if order.manager:
            create_notification(
                user=order.manager,
                notification_type='return_requested',
                title='রিটার্ন অনুরোধ',
                message=f'অর্ডার #{order.order_id} রিটার্নের জন্য অনুরোধ করা হয়েছে। কারণ: {reason}',
                order=order,
                send_email=True
            )
        else:
            messages.warning(request, 'ম্যানেজার অ্যাসাইন করা হয়নি। অ্যাডমিনকে জানান।')
        
        messages.success(request, f'অর্ডার #{order.order_id} রিটার্নের জন্য অনুরোধ করা হয়েছে।')
        return redirect('rider_dashboard')
    
    context = {
        'order': order,
    }
    return render(request, 'shop/rider_return_delivery.html', context)


# ============ MAP & GEOLOCATION ============
def user_map(request):
    """User-facing map with live location and zone check"""
    zones = Zone.objects.filter(is_active=True)
    
    context = {
        'zones': zones,
        'title': 'Service Zone Map - Live Location'
    }
    return render(request, 'shop/user_map.html', context)


def api_zones(request):
    """API endpoint to get all zones data (lat, lng, radius)"""
    zones = Zone.objects.filter(is_active=True)
    
    zones_data = []
    for zone in zones:
        if zone.latitude and zone.longitude:
            zones_data.append({
                'id': zone.id,
                'name': zone.name,
                'latitude': zone.latitude,
                'longitude': zone.longitude,
                'radius': zone.radius,
                'description': zone.description,
                'delivery_charge': str(zone.delivery_charge),
            })
    
    return JsonResponse({'zones': zones_data})


def api_check_location(request):
    """Check if user's location is within any service zone"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_lat = float(data.get('latitude'))
        user_lon = float(data.get('longitude'))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    
    # Use utility function
    result = check_location_in_zones(user_lat, user_lon)

    if request.user.is_authenticated:
        set_user_location(
            request.user.id,
            user_lat,
            user_lon,
            result['is_in_service'],
            result['service_zones'],
        )
    
    return JsonResponse({
        'user_location': {
            'latitude': user_lat,
            'longitude': user_lon,
        },
        'is_in_service': result['is_in_service'],
        'zones': result['service_zones'],
    })


def api_active_notices(request):
    """Get active admin notices as JSON"""
    try:
        now = timezone.now()
        notices = AdminNotice.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-priority', '-created_at').values(
            'id', 'title', 'message', 'icon', 'priority', 'color_bg', 'color_text', 'is_marquee'
        )[:3]  # Limit to 3 notices
        
        return JsonResponse({
            'success': True,
            'notices': list(notices)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def register_fcm_token(request):
    """Register FCM token for web push notifications"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        token = data.get('token')
        platform = data.get('platform', 'web')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'Token is required'}, status=400)
        
        from .firebase_config import register_device_token
        
        device_token = register_device_token(request.user, token, platform)
        
        if device_token:
            return JsonResponse({
                'success': True,
                'message': f'FCM token registered for {platform}',
                'token_id': device_token.id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to register FCM token'
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============ SHOPPING CART ============
def get_cart(request):
    """Get cart from session"""
    if 'cart' not in request.session:
        request.session['cart'] = {}
    return request.session['cart']


def set_cart(request, cart):
    """Save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True


def add_to_cart(request, product_id):
    """Add product to cart"""
    try:
        product = Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        messages.error(request, 'পণ্যটি পাওয়া যায়নি।')
        return redirect('home')
    
    cart = get_cart(request)
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'id': product.id,
            'title': product.title,
            'price': float(product.price),
            'unit': product.unit,
            'unit_display': product.get_unit_display(),
            'image': product.image.url if product.image else '/static/placeholder.png',
            'quantity': 1,
            'zone_id': product.zone_id,
            'zone_name': product.zone.name if product.zone else 'N/A'
        }
    
    set_cart(request, cart)
    messages.success(request, f'"{product.title}" কার্টে যোগ করা হয়েছে।')
    
    # Return to previous page or home
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def add_to_cart_ajax(request, product_id):
    """AJAX endpoint for adding product to cart"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'পণ্যটি পাওয়া যায়নি।'})
    
    cart = get_cart(request)
    product_id_str = str(product_id)
    
    # Check if already in cart
    quantity_before = cart.get(product_id_str, {}).get('quantity', 0)
    
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'id': product.id,
            'title': product.title,
            'price': float(product.price),
            'unit': product.unit,
            'unit_display': product.get_unit_display(),
            'image': product.image.url if product.image else '/static/placeholder.png',
            'quantity': 1,
            'zone_id': product.zone_id,
            'zone_name': product.zone.name if product.zone else 'N/A'
        }
    
    set_cart(request, cart)
    
    # Calculate total cart items
    total_items = sum(item['quantity'] for item in cart.values())
    
    return JsonResponse({
        'success': True,
        'message': f'"{product.title}" কার্টে যোগ করা হয়েছে',
        'product': {
            'id': product.id,
            'title': product.title,
            'price': float(product.price),
            'unit': product.get_unit_display(),
            'image': product.image.url if product.image else '/static/placeholder.png',
        },
        'cart_total_items': total_items,
    })


def view_cart(request):
    """Display cart items"""
    cart = get_cart(request)
    
    cart_items = []
    total_price = 0
    total_quantity = 0
    
    for product_id_str, item in cart.items():
        item_total = item['price'] * item['quantity']
        total_price += item_total
        total_quantity += item['quantity']
        
        item['total'] = item_total
        cart_items.append(item)
    
    zones = Zone.objects.filter(is_active=True).only('id', 'name', 'delivery_charge')
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': total_quantity,
        'zones': zones,
        'cart_empty': len(cart_items) == 0
    }
    
    return render(request, 'shop/cart.html', context)


def remove_from_cart(request, product_id):
    """Remove product from cart"""
    cart = get_cart(request)
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        product_title = cart[product_id_str]['title']
        del cart[product_id_str]
        set_cart(request, cart)
        messages.success(request, f'"{product_title}" কার্ট থেকে সরানো হয়েছে।')
    
    return redirect('view_cart')


def update_cart_quantity(request, product_id):
    """Update product quantity in cart"""
    if request.method == 'POST':
        quantity = request.POST.get('quantity', 1)
        cart = get_cart(request)
        product_id_str = str(product_id)
        
        try:
            quantity = int(quantity)
            if quantity > 0:
                if product_id_str in cart:
                    cart[product_id_str]['quantity'] = quantity
                    set_cart(request, cart)
                    messages.success(request, 'কার্ট আপডেট হয়েছে।')
            else:
                messages.error(request, 'পরিমাণ শূন্যের চেয়ে বেশি হতে হবে।')
        except ValueError:
            messages.error(request, 'অবৈধ পরিমাণ।')
    
    return redirect('view_cart')


def checkout(request):
    """Checkout page and order creation"""
    cart = get_cart(request)
    
    # Check if cart is empty
    if not cart:
        messages.error(request, 'আপনার কার্ট খালি আছে।')
        return redirect('view_cart')
    
    # Calculate totals
    cart_items = []
    total_price = 0
    
    for product_id_str, item in cart.items():
        item_total = item['price'] * item['quantity']
        total_price += item_total
        cart_items.append(item)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            try:
                zone = form.cleaned_data['zone']
                
                # Get location from POST
                latitude = request.POST.get('latitude')
                longitude = request.POST.get('longitude')
                
                # Convert to float if provided
                try:
                    latitude = float(latitude) if latitude else None
                    longitude = float(longitude) if longitude else None
                except ValueError:
                    latitude = None
                    longitude = None
                
                # Generate unique order ID
                order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                
                # Create order
                order = Order.objects.create(
                    order_id=order_id,
                    customer=request.user if request.user.is_authenticated else None,
                    zone=zone,
                    customer_phone=form.cleaned_data['phone'],
                    customer_email=form.cleaned_data['email'],
                    customer_address=form.cleaned_data['delivery_address'],
                    customer_city='',  # No city field in checkout
                    latitude=latitude,
                    longitude=longitude,
                    total_amount=total_price,
                    delivery_charge=zone.delivery_charge,
                    payment_method='cash',  # COD only
                    status='pending'
                )
                
                # Add items to order
                for product_id_str, item in cart.items():
                    try:
                        product = Product.objects.get(id=int(product_id_str))
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item['quantity'],
                            price=item['price']
                        )
                    except Product.DoesNotExist:
                        pass
                
                # Clear cart
                request.session['cart'] = {}
                request.session.modified = True
                
                messages.success(request, f'আপনার অর্ডার {order_id} সফলভাবে তৈরি হয়েছে!')
                
                # Create notification for customer
                if request.user.is_authenticated:
                    create_notification(
                        user=request.user,
                        notification_type='order_confirmation',
                        title='Order Confirmed',
                        message=f'Your order #{order_id} has been placed successfully.',
                        order=order
                    )
                
                # Create notifications for managers in the zone
                update_order_notifications(order, 'pending')
                
                # Redirect to order detail if user logged in
                if request.user.is_authenticated:
                    return redirect('order_detail', order_id=order.id)
                else:
                    # For guest users, just show a success message
                    return render(request, 'shop/order_success.html', {
                        'order_id': order_id,
                        'total_amount': total_price + zone.delivery_charge,
                        'zone_name': zone.name
                    })
            
            except Exception as e:
                messages.error(request, f'অর্ডার তৈরিতে সমস্যা: {str(e)}')
    else:
        # Pre-fill form if user is logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'full_name': f"{request.user.first_name or ''} {request.user.last_name or ''}".strip() or request.user.username,
                'email': request.user.email,
                'phone': request.user.profile.phone if hasattr(request.user, 'profile') else '',
                'delivery_address': request.user.profile.address if hasattr(request.user, 'profile') else '',
            }
        
        form = CheckoutForm(initial=initial_data)
    
    # Calculate total with delivery charge
    zones = Zone.objects.filter(is_active=True)
    default_delivery = zones.first().delivery_charge if zones else 50
    
    # Get Google Maps API Key
    api_key = get_google_maps_api_key()
    
    # Prepare zone data for JavaScript validation
    import json
    zones_data = []
    for zone in zones:
        zones_data.append({
            'id': zone.id,
            'name': zone.name,
            'latitude': zone.latitude,
            'longitude': zone.longitude,
            'radius': zone.radius,
            'delivery_charge': float(zone.delivery_charge)
        })
    zones_json = json.dumps(zones_data)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
        'zones': zones,
        'zones_json': zones_json,
        'default_delivery': default_delivery,
        'google_maps_api_key': api_key,
    }
    
    return render(request, 'shop/checkout.html', context)


# ============ NOTIFICATION VIEWS ============

def get_sound_for_notification(notification_type):
    """Map notification types to sound files"""
    sound_mapping = {
        'order_confirmation': 'order-confirmd.mp3',
        'order_processing': 'order-push.mp3',
        'order_picked': 'order-push.mp3',
        'order_in_transit': 'order-push.mp3',
        'order_delivered': 'order-push.mp3',
        'order_cancelled': 'order-push.mp3',
        'rider_assigned': 'manager-order.mp3',
        'rider_near': 'order-push.mp3',
        'payment_reminder': 'order-push.mp3',
        'general': 'order-push.mp3',
    }
    return sound_mapping.get(notification_type, 'order-push.mp3')


@login_required
def get_notifications(request):
    """Get all notifications for logged-in user with unread count"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_deleted=False
    ).order_by('-created_at')[:10]
    unread_count = get_unread_count(request.user)
    
    # Check if user has sound notifications enabled
    try:
        user_prefs = request.user.notification_preference
        enable_sound = user_prefs.enable_sound
    except:
        enable_sound = True
    
    notifications_data = []
    for notif in notifications:
        notifications_data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'type': notif.notification_type,
            'is_read': notif.is_read,
            'order_id': notif.order.id if notif.order else None,  # Use integer ID instead of string
            'order_number': notif.order.order_id if notif.order else None,  # Keep string for display
            'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M'),
            'sound_file': get_sound_for_notification(notif.notification_type) if enable_sound else None,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count,
        'enable_sound': enable_sound,
    })


@login_required
def mark_notification_read(request, notif_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notif_id, user=request.user)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    update_realtime_notification_status(notification)
    
    return JsonResponse({'status': 'success'})


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False, is_deleted=False).update(is_read=True)
    
    return JsonResponse({'status': 'success'})


@login_required
def notification_history(request):
    """View notification history page"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_deleted=False
    ).order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(notifications, 20)  # 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_count': notifications.count(),
        'title': 'Notification History'
    }
    return render(request, 'shop/notification_history.html', context)


@login_required
def delete_notification_view(request, notif_id):
    """Delete/archive a notification"""
    try:
        notification = get_object_or_404(Notification, id=notif_id, user=request.user)
        delete_notification(notification)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def clear_notifications(request):
    """Clear all notifications"""
    if request.method == 'POST':
        clear_all_notifications(request.user)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def notification_preferences(request):
    """View and edit notification preferences"""
    try:
        prefs = request.user.notification_preference
    except NotificationPreference.DoesNotExist:
        prefs = NotificationPreference.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Update preferences
        prefs.order_updates = request.POST.get('order_updates') == 'on'
        prefs.order_confirmation = request.POST.get('order_confirmation') == 'on'
        prefs.rider_assignments = request.POST.get('rider_assignments') == 'on'
        prefs.general_notifications = request.POST.get('general_notifications') == 'on'
        
        prefs.email_on_order_updates = request.POST.get('email_on_order_updates') == 'on'
        prefs.email_on_delivery = request.POST.get('email_on_delivery') == 'on'
        prefs.email_on_cancellation = request.POST.get('email_on_cancellation') == 'on'
        prefs.email_digests = request.POST.get('email_digests') == 'on'
        
        prefs.enable_sound = request.POST.get('enable_sound') == 'on'
        prefs.enable_browser_notifications = request.POST.get('enable_browser_notifications') == 'on'
        
        prefs.quiet_hours_enabled = request.POST.get('quiet_hours_enabled') == 'on'
        if request.POST.get('quiet_hours_start'):
            prefs.quiet_hours_start = request.POST.get('quiet_hours_start')
        if request.POST.get('quiet_hours_end'):
            prefs.quiet_hours_end = request.POST.get('quiet_hours_end')
        
        prefs.save()
        push_notification_preferences(request.user)
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('notification_preferences')
    
    context = {
        'prefs': prefs,
        'title': 'Notification Preferences'
    }
    return render(request, 'shop/notification_preferences.html', context)



