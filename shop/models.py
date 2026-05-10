from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal

# User Profile
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'গ্রাহক'),
        ('admin', 'অ্যাডমিন'),        # নতুন: Management panel access
        ('rider', 'রাইডার'),
        ('manager', 'ম্যানেজার'),  # অর্ডার গ্রহণ/প্রত্যাখ্যান করতে
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active_rider = models.BooleanField(default=False)  # Rider status
    
    # নতুন ফিল্ড: Manager এর জন্য
    zone_assigned = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, blank=True, 
                                     help_text="যে Zone এর জন্য এই Manager দায়ী")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    class Meta:
        verbose_name_plural = "User Profiles"


# Zone Management
class Zone(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    delivery_charge = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('50.00'))
    
    # Geolocation fields for live location tracking
    latitude = models.FloatField(null=True, blank=True, help_text="Center latitude of service zone")
    longitude = models.FloatField(null=True, blank=True, help_text="Center longitude of service zone")
    radius = models.IntegerField(default=2000, help_text="Service radius in meters (e.g. 2000 = 2km)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Zones"


# Category
class Category(models.Model):
    POSITION_CHOICES = [
        ('top', 'উপরে'),
        ('middle', 'মাঝখানে'),
        ('bottom', 'নিচে'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    image = models.ImageField(upload_to='category/', blank=True, null=True)
    description = models.TextField(blank=True)
    position = models.CharField(max_length=10, choices=POSITION_CHOICES, default='middle', 
                               help_text="ক্যাটেগরির অবস্থান (উপরে/মাঝখানে/নিচে)")
    display_order = models.PositiveIntegerField(default=0, help_text="প্রদর্শনের ক্রম")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            # Try to create a slug from the name
            base_slug = slugify(self.name)
            
            # If slugify returns empty (for non-ASCII text), create a fallback
            if not base_slug:
                # Use a transliteration approach or fallback to english-like slug
                import re
                # Remove non-alphanumeric characters and convert spaces to hyphens
                base_slug = re.sub(r'[^\w\s-]', '', self.name).strip().lower()
                base_slug = re.sub(r'[-\s]+', '-', base_slug)
                # If still empty, use a generic slug
                if not base_slug:
                    base_slug = f'category-{self.id}' if self.id else 'category'
            
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_order', 'name']


# Product
class Product(models.Model):
    UNIT_CHOICES = [
        ('kg', 'কিলোগ্রাম (kg)'),
        ('gram', 'গ্রাম (g)'),
        ('litre', 'লিটার (L)'),
        ('ml', 'মিলিলিটার (ml)'),
        ('piece', 'পিস'),
        ('packet', 'প্যাকেট'),
        ('box', 'বক্স'),
        ('bunch', 'বাঁড়ি/গুচ্ছ'),
        ('dozen', 'ডজন'),
    ]
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece', help_text="পণ্যের ইউনিট")
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=50)
    is_available = models.BooleanField(default=True)
    delivery_time = models.PositiveIntegerField(default=45, help_text="ডেলিভারি সময় (মিনিটে)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.zone.name})" if self.zone else self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Products"


# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'অপেক্ষায়'),          # নতুন অর্ডার - Manager এর অপেক্ষায়
        ('approved', 'অনুমোদিত'),        # Manager approved - Rider এর অপেক্ষায়
        ('confirmed', 'নিশ্চিত'),         # Rider assigned
        ('picked', 'রাইডার নিয়েছে'),    # Rider picked up product
        ('delivered', 'ডেলিভার হয়েছে'),  # Delivered
        ('return_requested', 'রিটার্ন অনুরোধ'),  # Rider requesting return
        ('cancelled', 'বাতিল'),           # Rejected or cancelled
    ]

    order_id = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    
    # নতুন: Manager এবং Rider tracking
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='managed_orders', 
                               limit_choices_to={'profile__role': 'manager'},
                               help_text="যে Manager এই অর্ডার approve করেছে")
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                             related_name='deliveries', 
                             limit_choices_to={'profile__role': 'rider'},
                             help_text="যে Rider deliver করবে")
    
    # Customer Details
    customer_phone = models.CharField(max_length=15)
    customer_email = models.EmailField()
    customer_address = models.TextField()
    customer_city = models.CharField(max_length=100)
    
    # Location (Google Maps সাথে capture করা)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address_formatted = models.TextField(blank=True, null=True, help_text="Google Maps থেকে formatted address")
    
    # Order Info
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    payment_method = models.CharField(max_length=20, default='cash')  # cash, card
    
    # নতুন: Manager approval tracking
    manager_approval_reason = models.TextField(blank=True, null=True, 
                                              help_text="Rejection reason if declined")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    manager_responded_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        customer_name = self.customer.username if self.customer else self.customer_phone
        return f"Order {self.order_id} - {customer_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Orders"


# Order Items
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.title} x{self.quantity}"

    class Meta:
        verbose_name_plural = "Order Items"


# Notification Model
class Notification(models.Model):
    # Simple notification types
    NOTIFICATION_TYPES = [
        ('order_confirmation', 'Order Confirmed'),
        ('order_processing', 'Order Processing'),
        ('order_picked', 'Order Picked'),
        ('order_in_transit', 'Order In Transit'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('rider_assigned', 'Rider Assigned'),
        ('rider_near', 'Rider Near You'),
        ('payment_reminder', 'Payment Reminder'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])


# Notification Preferences Model
class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preference')
    order_updates = models.BooleanField(default=True, help_text='Get notified on order status updates')
    order_confirmation = models.BooleanField(default=True, help_text='Get notified when order is confirmed')
    rider_assignments = models.BooleanField(default=True, help_text='Get notified when rider is assigned')
    general_notifications = models.BooleanField(default=True, help_text='Get notified about general updates')
    email_on_order_updates = models.BooleanField(default=True, help_text='Send email on order updates')
    email_on_delivery = models.BooleanField(default=True, help_text='Send email when order is delivered')
    email_on_cancellation = models.BooleanField(default=True, help_text='Send email if order is cancelled')
    email_digests = models.BooleanField(default=False, help_text='Receive daily digest of all notifications')
    enable_sound = models.BooleanField(default=True, help_text='Play sound for new notifications')
    enable_browser_notifications = models.BooleanField(default=True, help_text='Show browser notifications')
    quiet_hours_enabled = models.BooleanField(default=False, help_text='Enable quiet hours (no notifications)')
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text='Quiet hours start time (HH:MM)')
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text='Quiet hours end time (HH:MM)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"


# FCM Device Token Model for Mobile Push Notifications
class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True, help_text='FCM device token')
    platform = models.CharField(max_length=20, choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')], default='android')
    device_id = models.CharField(max_length=100, blank=True, help_text='Unique device identifier')
    is_active = models.BooleanField(default=True, help_text='Whether this token is still active')
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'
        unique_together = ['user', 'device_id']

    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.device_id})"


# Hero Slide Model - For Homepage Carousel
class HeroSlide(models.Model):
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    button_text = models.CharField(max_length=100, default="Order Now")
    button_link = models.CharField(max_length=300, default="/register/", help_text="URL to navigate when button is clicked")
    background_image = models.ImageField(upload_to='hero_slides/')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order of slides")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        verbose_name_plural = "Hero Slides"
    
    def __str__(self):
        return f"{self.title} (Order: {self.order})"


# User Behavior Tracking for Recommendations
class ProductView(models.Model):
    """Track which products users view"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, help_text="For anonymous users")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'product', 'session_id']
        ordering = ['-viewed_at']
        verbose_name_plural = "Product Views"

    def __str__(self):
        user_info = self.user.username if self.user else f"Anonymous ({self.session_id})"
        return f"{user_info} viewed {self.product.title}"


class UserPreference(models.Model):
    """Track user preferences for recommendations"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_categories = models.ManyToManyField(Category, blank=True)
    preferred_zones = models.ManyToManyField(Zone, blank=True)
    last_location_lat = models.FloatField(null=True, blank=True)
    last_location_lng = models.FloatField(null=True, blank=True)
    favorite_products = models.ManyToManyField(Product, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"

    class Meta:
        verbose_name_plural = "User Preferences"


class ProductRecommendation(models.Model):
    """Cache personalized recommendations"""
    RECOMMENDATION_TYPES = [
        ('location_based', 'Location Based'),
        ('category_based', 'Category Based'),
        ('purchase_history', 'Purchase History'),
        ('popular', 'Popular Products'),
        ('trending', 'Trending Now'),
        ('similar_users', 'Similar Users'),
        ('time_based', 'Time Based'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0, help_text="Recommendation score (0-1)")
    reason = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-score', '-created_at']
        verbose_name_plural = "Product Recommendations"

    def __str__(self):
        return f"{self.product.title} for {self.user.username} ({self.score:.2f})"

    def is_expired(self):
        return timezone.now() > self.expires_at


# Admin Notice/Announcement Model
class AdminNotice(models.Model):
    """Admin notices that display as marquee on user dashboard"""
    title = models.CharField(max_length=200)
    message = models.TextField(help_text="Marquee message for users")
    icon = models.CharField(max_length=50, default='fas fa-bell', help_text="FontAwesome icon class")
    
    PRIORITY_CHOICES = [
        ('low', '🟢 Low'),
        ('medium', '🟡 Medium'),
        ('high', '🔴 High'),
        ('critical', '⚫ Critical'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    color_bg = models.CharField(max_length=20, default='#28a745', help_text="Background color (hex)")
    color_text = models.CharField(max_length=20, default='#ffffff', help_text="Text color (hex)")
    
    is_active = models.BooleanField(default=True)
    is_marquee = models.BooleanField(default=True, help_text="Show as scrolling marquee")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(help_text="Notice visible from this date")
    end_date = models.DateTimeField(help_text="Notice visible until this date")
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name_plural = "Admin Notices"
    
    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"
    
    @property
    def is_visible(self):
        """Check if notice is visible based on date range"""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
