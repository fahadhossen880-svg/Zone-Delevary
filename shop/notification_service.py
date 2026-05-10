"""
Notification Service - Handles creating notifications and sending emails
"""
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import time
from .models import Notification, NotificationPreference, Order
from .firebase_config import push_realtime_notification


def should_notify_user(user, notification_type):
    """Check if user wants to receive this type of notification"""
    try:
        prefs = user.notification_preference
    except NotificationPreference.DoesNotExist:
        # Create default preferences if they don't exist
        prefs = NotificationPreference.objects.create(user=user)
    
    # Check quiet hours
    if prefs.quiet_hours_enabled:
        current_time = timezone.now().time()
        start = prefs.quiet_hours_start or time(22, 0)  # Default 10 PM
        end = prefs.quiet_hours_end or time(8, 0)  # Default 8 AM
        
        if start < end:
            if start <= current_time < end:
                return False
        else:  # Quiet hours span midnight
            if current_time >= start or current_time < end:
                return False
    
    # Check notification type preferences for in-app notifications
    if notification_type == 'order_confirmation':
        return prefs.order_confirmation
    elif notification_type in ['order_processing', 'order_picked', 'order_in_transit']:
        return prefs.order_updates
    elif notification_type == 'order_delivered':
        return prefs.order_updates
    elif notification_type == 'order_cancelled':
        return prefs.order_updates
    elif notification_type == 'rider_assigned':
        return prefs.rider_assignments
    elif notification_type == 'rider_near':
        return prefs.order_updates
    elif notification_type in ['general', 'payment_reminder']:
        return prefs.general_notifications
    
    return True


def can_play_sound(user):
    """Check if user has sound notifications enabled"""
    try:
        prefs = user.notification_preference
        return prefs.enable_sound
    except NotificationPreference.DoesNotExist:
        return True  # Default to enabled


def send_notification_email(notification):
    """Send email notification to user"""
    try:
        prefs = notification.user.notification_preference
    except NotificationPreference.DoesNotExist:
        return False
    
    # Check which type of email notifications are enabled
    notification_type = notification.notification_type
    
    should_send_email = False
    if notification_type == 'order_delivered' and prefs.email_on_delivery:
        should_send_email = True
    elif notification_type == 'order_cancelled' and prefs.email_on_cancellation:
        should_send_email = True
    elif notification_type in ['order_confirmation', 'order_processing', 'order_picked', 'rider_assigned'] and prefs.email_on_order_updates:
        should_send_email = True
    
    if not should_send_email:
        return False
    
    try:
        # Prepare email context
        context = {
            'user': notification.user,
            'notification': notification,
            'order': notification.order,
            'site_name': 'ZoneDelivery',
        }
        
        # Render email template
        html_message = render_to_string('shop/email/notification_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=notification.title,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Mark email as sent
        notification.email_sent = True
        notification.save(update_fields=['email_sent'])
        
        return True
    except Exception as e:
        print(f"Error sending notification email: {str(e)}")
        return False


def create_notification(user, notification_type, title, message, order=None, send_email=True):
    """
    Create a notification for a user
    
    Args:
        user: User instance
        notification_type: Type of notification (from NOTIFICATION_TYPES choices)
        title: Notification title
        message: Notification message
        order: Related Order instance (optional)
        send_email: Whether to send email notification (default: True)
    
    Returns:
        Notification instance or None if not created
    """
    # Check if user wants this notification
    if not should_notify_user(user, notification_type):
        return None
    
    try:
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            order=order,
            is_read=False,
        )
        
        # Push notification to Firebase Realtime DB for live sync
        # NOTE: Firebase errors should not break the notification system
        try:
            push_realtime_notification(notification)
        except Exception as firebase_err:
            print(f"⚠️  Firebase sync failed (notification still created): {firebase_err}")

        # Send email notification if enabled and requested
        if send_email:
            try:
                send_notification_email(notification)
            except Exception as email_err:
                print(f"⚠️  Email send failed (notification still created): {email_err}")
        
        print(f"✅ Notification created for {user.username}: {title}")
        return notification
    except Exception as e:
        print(f"❌ Error creating notification: {str(e)}")
        return None


def create_batch_notifications(users, notification_type, title, message, order=None):
    """
    Create notifications for multiple users at once
    
    Args:
        users: List of User instances
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        order: Related Order instance (optional)
    
    Returns:
        List of created Notification instances
    """
    notifications = []
    for user in users:
        notif = create_notification(user, notification_type, title, message, order, send_email=False)
        if notif:
            notifications.append(notif)
    
    return notifications


def update_order_notifications(order, status):
    """
    Handle notifications when order status changes
    
    Args:
        order: Order instance
        status: New order status
    """
    if status == 'pending':
        # Notification for managers in the zone
        if order.zone:
            manager_users = User.objects.filter(
                profile__role='manager',
                profile__zone_assigned=order.zone
            )
            
            manager_count = manager_users.count()
            print(f"[NOTIFICATION] Order {order.order_id}: Found {manager_count} managers for zone '{order.zone.name}'")
            
            customer_name = order.customer.get_full_name() or order.customer.username if order.customer else order.customer_phone
            title = '🔔 New Order Received'
            message = f'New Order #{order.order_id} from {customer_name} - ৳{order.total_amount} (Zone: {order.zone.name})'
            
            for manager in manager_users:
                notif = create_notification(
                    user=manager,
                    notification_type='general',  # Changed from 'rider_assigned' to 'general' for manager notifications
                    title=title,
                    message=message,
                    order=order,
                    send_email=True
                )
                print(f"[NOTIFICATION] Manager notification created for {manager.username}: {notif.id if notif else 'FAILED'}")
        else:
            print(f"[NOTIFICATION] Order {order.order_id}: No zone assigned")
    
    elif status == 'approved':
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_processing',
                title='Order Approved ✓',
                message=f'Your order #{order.order_id} has been approved. A rider will be assigned shortly.',
                order=order,
            )
    
    elif status == 'confirmed':
        if order.customer and order.rider:
            create_notification(
                user=order.customer,
                notification_type='rider_assigned',
                title='Rider Assigned',
                message=f'Rider {order.rider.get_full_name() or order.rider.username} is on the way to pick up your order.',
                order=order,
            )
    
    elif status == 'picked':
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_picked',
                title='Order Picked Up',
                message=f'Your order #{order.order_id} has been picked up and is on the way.',
                order=order,
            )
        
        if order.rider:
            create_notification(
                user=order.rider,
                notification_type='order_picked',
                title='Order Picked',
                message=f'You have picked up order #{order.order_id}. Head to delivery address.',
                order=order,
            )
    
    elif status == 'delivered':
        # BUG FIX #4: Update delivered_at timestamp
        order.delivered_at = timezone.now()
        order.save()
        
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_delivered',
                title='Order Delivered 🎉',
                message=f'Your order #{order.order_id} has been delivered. Thank you for using ZoneDelivery!',
                order=order,
            )
        
        if order.rider:
            create_notification(
                user=order.rider,
                notification_type='order_delivered',
                title='Delivery Completed',
                message=f'Order #{order.order_id} marked as delivered.',
                order=order,
            )
    
    elif status == 'cancelled':
        if order.customer:
            reason = order.manager_approval_reason or 'No reason provided'
            create_notification(
                user=order.customer,
                notification_type='order_cancelled',
                title='Order Cancelled',
                message=f'Your order #{order.order_id} has been cancelled. Reason: {reason}',
                order=order,
            )


def get_unread_count(user):
    """Get unread notification count for user"""
    return Notification.objects.filter(
        user=user,
        is_read=False,
        is_deleted=False
    ).count()


def get_notifications(user, limit=10, skip_deleted=True):
    """Get notifications for user"""
    query = Notification.objects.filter(user=user)
    if skip_deleted:
        query = query.filter(is_deleted=False)
    return query.order_by('-created_at')[:limit]


def delete_notification(notification):
    """Soft delete a notification"""
    notification.is_deleted = True
    notification.save(update_fields=['is_deleted'])


def clear_all_notifications(user):
    """Clear all notifications for a user (soft delete)"""
    Notification.objects.filter(user=user, is_deleted=False).update(is_deleted=True)
