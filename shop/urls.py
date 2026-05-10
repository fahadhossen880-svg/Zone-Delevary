from django.urls import path, re_path
from . import views
from . import admin_views

urlpatterns = [
    # Home & Auth
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    re_path(r'^category/(?P<slug>[-\w]+)/$', views.category_detail, name='category_detail'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('google-login/', views.google_login, name='google_login'),
    path('google-callback/', views.google_callback, name='google_callback'),
    path('auth/google/callback/', views.google_callback),
    path('logout/', views.user_logout, name='logout'),
    path('admin-register/', views.admin_register, name='admin_register'),
    
    # User Profile
    path('profile/', views.profile, name='profile'),
    
    # Orders
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Shopping Cart
    path('cart/', views.view_cart, name='view_cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('api/add-to-cart/<int:product_id>/', views.add_to_cart_ajax, name='add_to_cart_ajax'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:product_id>/', views.update_cart_quantity, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Rider
    path('rider/dashboard/', views.rider_dashboard, name='rider_dashboard'),
    path('rider/order/<int:order_id>/', views.rider_order_detail, name='rider_order_detail'),
    path('rider/order/<int:order_id>/return/', views.rider_return_delivery, name='rider_return_delivery'),
    
    # Map & Geolocation
    path('map/', views.user_map, name='user_map'),
    path('api/zones/', views.api_zones, name='api_zones'),
    path('api/check-location/', views.api_check_location, name='api_check_location'),
    path('api/active-notices/', views.api_active_notices, name='api_active_notices'),
    
    # FCM Token Registration
    path('api/register-fcm-token/', views.register_fcm_token, name='register_fcm_token'),
    
    # ============ ADMIN PANEL (CUSTOM) ============
    # Admin Dashboard
    path('dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    
    # Zone Management
    path('dashboard/zones/', admin_views.admin_zones, name='admin_zones'),
    path('dashboard/zone/add/', admin_views.admin_zone_add, name='admin_zone_add'),
    path('dashboard/zone/<int:zone_id>/edit/', admin_views.admin_zone_edit, name='admin_zone_edit'),
    path('dashboard/zone/<int:zone_id>/delete/', admin_views.admin_zone_delete, name='admin_zone_delete'),
    
    # Category Management
    path('dashboard/categories/', admin_views.admin_categories, name='admin_categories'),
    path('dashboard/category/add/', admin_views.admin_category_add, name='admin_category_add'),
    path('dashboard/category/<int:cat_id>/edit/', admin_views.admin_category_edit, name='admin_category_edit'),
    path('dashboard/category/<int:cat_id>/delete/', admin_views.admin_category_delete, name='admin_category_delete'),
    
    # Product Management
    path('dashboard/products/', admin_views.admin_products, name='admin_products'),
    path('dashboard/product/add/', admin_views.admin_product_add, name='admin_product_add'),
    path('dashboard/product/<int:prod_id>/edit/', admin_views.admin_product_edit, name='admin_product_edit'),
    path('dashboard/product/<int:prod_id>/delete/', admin_views.admin_product_delete, name='admin_product_delete'),
    
    # User Management
    path('dashboard/users/', admin_views.admin_users, name='admin_users'),
    path('dashboard/user/<int:user_id>/role/', admin_views.admin_user_role_change, name='admin_user_role'),
    
    # Order Management
    path('dashboard/orders/', admin_views.admin_orders, name='admin_orders'),
    path('dashboard/order/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    
    # ============ MANAGER PANEL ============
    path('manager/', admin_views.manager_dashboard, name='manager_dashboard'),
    path('manager/order/<int:order_id>/approve/', admin_views.manager_approve_order, name='manager_approve_order'),
    path('manager/order/<int:order_id>/assign-rider/', admin_views.manager_assign_rider, name='manager_assign_rider'),
    path('manager/order/<int:order_id>/return-request/', admin_views.manager_return_request, name='manager_return_request'),
    path('manager/riders/', admin_views.manager_riders, name='manager_riders'),
    
    # Manager Product Management
    path('manager/products/', admin_views.manager_products, name='manager_products'),
    path('manager/product/add/', admin_views.manager_product_add, name='manager_product_add'),
    path('manager/product/<int:prod_id>/edit/', admin_views.manager_product_edit, name='manager_product_edit'),
    path('manager/product/<int:prod_id>/delete/', admin_views.manager_product_delete, name='manager_product_delete'),
    
    # Manager Category Management
    path('manager/categories/', admin_views.manager_categories, name='manager_categories'),
    path('manager/category/add/', admin_views.manager_category_add, name='manager_category_add'),
    path('manager/category/<int:cat_id>/edit/', admin_views.manager_category_edit, name='manager_category_edit'),
    path('manager/category/<int:cat_id>/delete/', admin_views.manager_category_delete, name='manager_category_delete'),
    
    # ============ HERO SLIDES ============
    path('dashboard/hero-slides/', admin_views.admin_hero_slides, name='admin_hero_slides'),
    path('dashboard/hero-slide/add/', admin_views.admin_hero_slide_add, name='admin_hero_slide_add'),
    path('dashboard/hero-slide/<int:slide_id>/edit/', admin_views.admin_hero_slide_edit, name='admin_hero_slide_edit'),
    path('dashboard/hero-slide/<int:slide_id>/delete/', admin_views.admin_hero_slide_delete, name='admin_hero_slide_delete'),
    
    # ============ RECOMMENDATION MANAGEMENT ============
    path('dashboard/recommendations/', admin_views.admin_recommendations, name='admin_recommendations'),
    path('dashboard/recommendation-settings/', admin_views.admin_recommendation_settings, name='admin_recommendation_settings'),
    
    # ============ ADMIN NOTICES ============
    path('dashboard/notices/', admin_views.admin_notices, name='admin_notices'),
    path('dashboard/notice/add/', admin_views.admin_notice_add, name='admin_notice_add'),
    path('dashboard/notice/<int:notice_id>/edit/', admin_views.admin_notice_edit, name='admin_notice_edit'),
    path('dashboard/notice/<int:notice_id>/delete/', admin_views.admin_notice_delete, name='admin_notice_delete'),
    
    # ============ NOTIFICATION URLS ============
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notification/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notification/<int:notif_id>/delete/', views.delete_notification_view, name='delete_notification'),
    path('api/notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('notifications/', views.notification_history, name='notification_history'),
    path('notifications/preferences/', views.notification_preferences, name='notification_preferences'),
]
