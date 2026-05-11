"""
Simplified Notification Service - Direct Firebase Realtime DB integration
- No quiet hours
- No email notifications
- All notifications go to Firebase Realtime DB in real-time
"""
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification, NotificationPreference, Order
from .firebase_config import push_realtime_notification, send_fcm_notification_to_user


def create_notification(user, notification_type, title, message, order=None, send_email=False):
    """
    সরল: Create a notification for a user and sync to Firebase immediately
    
    Args:
        user: User instance
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        order: Related Order instance (optional)
        send_email: legacy flag, currently ignored in the simplified system
    
    Returns:
        Notification instance or None if creation failed
    """
    try:
        # Create notification in PostgreSQL DB
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            order=order,
            is_read=False,
        )
        
        # ✅ Sync to Firebase Realtime DB immediately (সাইট এর notification box এ update হবে)
        try:
            push_realtime_notification(notification)
            print(f"✅ Notification synced to Firebase: {notification.id}")
        except Exception as firebase_err:
            print(f"⚠️ Firebase sync failed: {firebase_err}")

        # ✅ Send FCM push notification to mobile devices
        try:
            fcm_data = {
                'notification_id': str(notification.id),
                'type': notification.notification_type,
                'order_id': notification.order.order_id if notification.order else None,
            }
            send_fcm_notification_to_user(user, title, message, fcm_data)
        except Exception as fcm_err:
            print(f"⚠️ FCM send failed: {fcm_err}")
        
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
        notif = create_notification(user, notification_type, title, message, order)
        if notif:
            notifications.append(notif)
    
    return notifications


def update_order_notifications(order, status):
    """
    সরল: Handle notifications when order status changes
    সব notification সরাসরি Firebase Realtime DB তে যাবে
    
    Args:
        order: Order instance
        status: New order status
    """
    if status == 'pending':
        # নতুন অর্ডার এসেছে - Zone এর সব Managers কে notify করো
        if order.zone:
            manager_users = User.objects.filter(
                profile__role='manager',
                profile__zone_assigned=order.zone
            )
            
            manager_count = manager_users.count()
            print(f"[NOTIFICATION] Order {order.order_id}: Found {manager_count} managers")
            
            customer_name = order.customer.get_full_name() or order.customer.username if order.customer else order.customer_phone
            title = '🔔 নতুন অর্ডার'
            message = f'Order #{order.order_id} - {customer_name} - ৳{order.total_amount}'
            
            for manager in manager_users:
                create_notification(
                    user=manager,
                    notification_type='general',
                    title=title,
                    message=message,
                    order=order
                )
    
    elif status == 'approved':
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_processing',
                title='অর্ডার অনুমোদিত ✓',
                message=f'Order #{order.order_id} অনুমোদিত হয়েছে',
                order=order,
            )
    
    elif status == 'confirmed':
        if order.customer and order.rider:
            create_notification(
                user=order.customer,
                notification_type='rider_assigned',
                title='রাইডার নির্ধারিত',
                message=f'{order.rider.get_full_name() or order.rider.username} আপনার অর্ডার পিক আপ করতে আসছে',
                order=order,
            )
    
    elif status == 'picked':
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_picked',
                title='অর্ডার পিক আপ হয়েছে',
                message=f'Order #{order.order_id} পিক আপ হয়েছে এবং ডেলিভারিতে যাচ্ছে',
                order=order,
            )
        
        if order.rider:
            create_notification(
                user=order.rider,
                notification_type='order_picked',
                title='অর্ডার পিক আপ',
                message=f'Order #{order.order_id} ডেলিভারি এড্রেসে নিয়ে যান',
                order=order,
            )
    
    elif status == 'delivered':
        # আপডেট delivered_at timestamp
        order.delivered_at = timezone.now()
        order.save()
        
        if order.customer:
            create_notification(
                user=order.customer,
                notification_type='order_delivered',
                title='অর্ডার ডেলিভার হয়েছে 🎉',
                message=f'Order #{order.order_id} ডেলিভার হয়েছে। ধন্যবাদ!',
                order=order,
            )
        
        if order.rider:
            create_notification(
                user=order.rider,
                notification_type='order_delivered',
                title='ডেলিভারি সম্পন্ন',
                message=f'Order #{order.order_id} ডেলিভার করা হয়েছে',
                order=order,
            )
    
    elif status == 'cancelled':
        if order.customer:
            reason = order.manager_approval_reason or 'কোনো কারণ প্রদান করা হয়নি'
            create_notification(
                user=order.customer,
                notification_type='order_cancelled',
                title='অর্ডার বাতিল',
                message=f'Order #{order.order_id} বাতিল করা হয়েছে',
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
