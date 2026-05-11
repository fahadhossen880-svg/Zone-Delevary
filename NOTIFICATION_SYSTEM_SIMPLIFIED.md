# 🔔 সরলীকৃত নোটিফিকেশন সিস্টেম

## সিস্টেম পরিবর্তন সারসংক্ষেপ

আপনার জটিল নোটিফিকেশন সিস্টেম সম্পূর্ণভাবে সিম্পলিফাই করা হয়েছে।

### ❌ বাদ দেওয়া হয়েছে:
- ❌ **Quiet Hours System** - এখন সারাদিন notification পাবে
- ❌ **Sound Notifications** - সাউন্ড সিস্টেম সম্পূর্ণ সরানো হয়েছে
- ❌ **Email Notifications** - ইমেইল নোটিফিকেশন বন্ধ করা হয়েছে
- ❌ **Complex Preferences** - সব প্রিফারেন্স অপশন দূর করা হয়েছে

### ✅ রাখা হয়েছে:
- ✅ **Firebase Realtime DB Sync** - সাইটের notification box এ real-time আপডেট
- ✅ **FCM Push Notifications** - মোবাইলে পুশ notification
- ✅ **PostgreSQL Storage** - DB তে notification সংরক্ষণ
- ✅ **Toast UI** - সাইটে toast notification

---

## নতুন আর্কিটেকচার

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMPLIFIED FLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Event (Order Created/Updated)                             │
│           ↓                                                  │
│  Django Backend → create_notification()                    │
│           ↓                                                  │
│  ┌─────────────────────────────────────────────────┐       │
│  │  Save to PostgreSQL DB (Notification Table)    │       │
│  └─────────────────────────────────────────────────┘       │
│           ↓                                                  │
│  ┌─────────────────────────────────────────────────┐       │
│  │  Push to Firebase Realtime DB                  │       │
│  │  (Site Notification Box Updates)               │       │
│  └─────────────────────────────────────────────────┘       │
│           ↓                                                  │
│  ┌─────────────────────────────────────────────────┐       │
│  │  Send FCM Push to Mobile                       │       │
│  └─────────────────────────────────────────────────┘       │
│           ↓                                                  │
│  User Gets Instant Notification                           │
│  - On Website (Toast + notification box)                  │
│  - On Mobile (FCM notification)                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## কোড পরিবর্তন

### 1️⃣ Models.py - সিম্পলিফাইড NotificationPreference

**আগে:**
```python
class NotificationPreference(models.Model):
    user = OneToOneField(User)
    order_updates = BooleanField()
    order_confirmation = BooleanField()
    rider_assignments = BooleanField()
    general_notifications = BooleanField()
    email_on_order_updates = BooleanField()
    email_on_delivery = BooleanField()
    email_on_cancellation = BooleanField()
    email_digests = BooleanField()
    enable_sound = BooleanField()
    enable_browser_notifications = BooleanField()
    quiet_hours_enabled = BooleanField()
    quiet_hours_start = TimeField()
    quiet_hours_end = TimeField()
```

**এখন:**
```python
class NotificationPreference(models.Model):
    user = OneToOneField(User)
    enabled = BooleanField(default=True)  # সব সময় True
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

---

### 2️⃣ notification_service.py - সরলীকৃত লজিক

**আগে:** 80+ লাইন complex logic

**এখন:** মাত্র 40 লাইন সরল কোড

```python
def create_notification(user, notification_type, title, message, order=None):
    """
    সরল: Create notification for user
    """
    try:
        # 1. Save to PostgreSQL
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            order=order,
            is_read=False,
        )
        
        # 2. Sync to Firebase Realtime DB
        try:
            push_realtime_notification(notification)
        except Exception as e:
            print(f"⚠️ Firebase sync failed: {e}")

        # 3. Send FCM push to mobile
        try:
            fcm_data = {
                'notification_id': str(notification.id),
                'type': notification.notification_type,
                'order_id': notification.order.order_id if notification.order else None,
            }
            send_fcm_notification_to_user(user, title, message, fcm_data)
        except Exception as e:
            print(f"⚠️ FCM send failed: {e}")
        
        print(f"✅ Notification created: {notification.id}")
        return notification
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None
```

---

### 3️⃣ Firebase Config - পরিষ্কার

- ✅ `push_realtime_notification()` - সাইট notification box এ sync করে
- ✅ `send_fcm_notification()` - মোবাইলে পাঠায়
- ❌ `push_notification_preferences()` - সরানো হয়েছে
- ❌ `update_realtime_notification_status()` - সরল করা হয়েছে

---

### 4️⃣ Frontend (base.html) - সাউন্ড সরানো

**সরানো হয়েছে:**
- ❌ Sound URLs data attributes
- ❌ `playNotificationSound()` function
- ❌ Audio cache
- ❌ previousUnreadCount tracking

**রাখা হয়েছে:**
- ✅ Toast notification display
- ✅ Notification modal
- ✅ FCM token registration
- ✅ Real-time polling every 30 seconds

---

### 5️⃣ Views - সিম্পলিফাইড API

**get_notifications() API:**

```python
@login_required
def get_notifications(request):
    """সরল: সব notification পান"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_deleted=False
    ).order_by('-created_at')[:10]
    
    notifications_data = [
        {
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'type': notif.notification_type,
            'is_read': notif.is_read,
            'order_id': notif.order.id if notif.order else None,
            'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for notif in notifications
    ]
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': get_unread_count(request.user),
    })
```

---

## নোটিফিকেশন ফ্লো - ধাপে ধাপে

### অর্ডার তৈরি হলে কি ঘটে?

```
1. Customer → Order Create
   ↓
2. Backend: update_order_notifications(order, 'pending')
   ↓
3. Manager কে notification create হয়:
   ├─ Title: "🔔 নতুন অর্ডার"
   ├─ Message: "Order #XXX - Customer Name - ৳Amount"
   └─ Type: 'general'
   ↓
4. Notification save হয় DB তে
   ├─ PostgreSQL: Notification table
   └─ Created_at: current timestamp
   ↓
5. Firebase Realtime DB তে sync হয়:
   notifications/{manager_id}/{notification_id}
   ↓
6. FCM Push পাঠানো হয় মোবাইলে
   ↓
7. Website তে:
   ├─ প্রতি 30 সেকেন্ডে API fetch হয়
   ├─ নতুন notification পেলে
   ├─ Toast দেখানো হয়
   └─ Notification box update হয়
   ↓
8. Mobile এ:
   ├─ FCM notification পাওয়া যায়
   ├─ Foreground/Background handler চলে
   └─ System notification দেখানো হয়
```

---

## Database Schema - Simple

### PostgreSQL

```sql
-- Notification Table (unchanged)
CREATE TABLE notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(50),
    title VARCHAR(200),
    message TEXT,
    order_id INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP AUTO_NOW_ADD,
    FOREIGN KEY (user_id) REFERENCES auth_user(id),
    FOREIGN KEY (order_id) REFERENCES order(id)
);

-- NotificationPreference Table (simplified)
CREATE TABLE notificationpreference (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP AUTO_NOW_ADD,
    updated_at TIMESTAMP AUTO_NOW,
    FOREIGN KEY (user_id) REFERENCES auth_user(id)
);
```

### Firebase Realtime DB

```json
{
  "notifications": {
    "user_123": {
      "notif_456": {
        "id": 456,
        "user_id": 123,
        "type": "order_confirmation",
        "title": "অর্ডার নিশ্চিত",
        "message": "Your order confirmed",
        "order_id": 789,
        "is_read": false,
        "created_at": "2026-05-11T10:30:00Z"
      }
    }
  }
}
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/get-notifications/` | GET | সব notification পান (সাইট notification box) |
| `/notification/{id}/read/` | POST | Notification mark as read |
| `/notification/{id}/delete/` | POST | Notification delete |
| `/notification/clear-all/` | POST | সব notification clear করুন |
| `/notification-preferences/` | GET/POST | নোটিফিকেশন প্রিফারেন্স (এখন সব enabled) |

---

## সুবিধা এই সিম্পলিফিকেশনে

✅ **সহজ রক্ষণাবেক্ষণ** - কম কোড, কম bug
✅ **দ্রুত notification** - সরাসরি Firebase sync
✅ **Real-time updates** - সাইট notification box instantly update হয়
✅ **কম ডাটাবেস query** - কোন preference check নেই
✅ **Mobile + Web both** - FCM + Firebase dual push
✅ **সবসময় notification** - কোন quiet hours নেই
✅ **সাউন্ড ছাড়াই clear** - UI তে পরিষ্কার notification

---

## অর্ডার Status সাথে সব Notification Types

```python
# Order Status → Notification Recipients

'pending' → Managers (Zone এর)
'approved' → Customer
'confirmed' → Customer + Rider
'picked' → Customer + Rider
'delivered' → Customer + Rider
'cancelled' → Customer
```

---

## টেস্ট করার জন্য

### ম্যানুয়ালি Notification তৈরি করুন:

```python
from django.contrib.auth.models import User
from shop.models import Order
from shop.notification_service import create_notification

# ইউজার খুঁজুন
user = User.objects.get(username='manager')

# Notification তৈরি করুন
create_notification(
    user=user,
    notification_type='general',
    title='🔔 টেস্ট নোটিফিকেশন',
    message='এটি একটি টেস্ট নোটিফিকেশন',
    order=None
)
```

### Django Shell এ:
```bash
python manage.py shell
```

---

## সম্পর্কিত ফাইলগুলি

| ফাইল | পরিবর্তন |
|------|----------|
| `shop/models.py` | NotificationPreference সরল করা হয়েছে |
| `shop/notification_service.py` | সব জটিলতা সরানো, শুধু basic logic |
| `shop/firebase_config.py` | push_notification_preferences সরানো |
| `shop/views.py` | get_sound_for_notification সরানো |
| `shop/templates/shop/base.html` | সাউন্ড ফাংশন সরানো, Toast রাখা |
| `shop/migrations/0003_*` | DB schema আপডেট |

---

## মাইগ্রেশন প্রয়োজন

✅ সব migrations প্রয়োগ করা হয়েছে:

```bash
python manage.py makemigrations  # Already done
python manage.py migrate          # Already done
```

---

**সিস্টেম এখন production ready! 🚀**

সব notification এখন:
- ✅ সরাসরি Firebase Realtime DB এ sync হয়
- ✅ সাইটের notification box এ real-time দেখা যায়
- ✅ মোবাইলে FCM push পাঠানো হয়
- ✅ কোনো জটিলতা নেই
