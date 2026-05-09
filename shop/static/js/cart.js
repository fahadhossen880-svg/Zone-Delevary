/**
 * AJAX Cart Management
 * Handles Add to Cart with animated notifications
 */

function isUserAuthenticated() {
    return document.body.dataset.isAuthenticated === '1';
}

function getLoginUrl() {
    return document.body.dataset.loginUrl || '/login/';
}

// Show toast notification
function showToast(title, message, type = 'success') {
    const toastHTML = `
        <div class="toast align-items-center border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body" style="background: linear-gradient(135deg, #52C77B 0%, #3DA670 100%); color: white; border-radius: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <i class="fas fa-check-circle" style="font-size: 1.5rem;"></i>
                        <div>
                            <strong>${title}</strong>
                            <p style="margin: 5px 0 0 0; font-size: 0.9rem;">${message}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Create container if not exists
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            right: auto;
            z-index: 9999;
        `;
        document.body.appendChild(toastContainer);
    }
    
    // Add toast to container
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = toastHTML;
    const toastElement = tempDiv.firstElementChild;
    toastContainer.appendChild(toastElement);
    
    // Initialize Bootstrap toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove element after hide
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Add to cart with AJAX
function addToCartAjax(productId, clickEvent) {
    if (!isUserAuthenticated()) {
        window.location.href = getLoginUrl();
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    
    // Show loading state
    const button = clickEvent?.target?.closest('.btn');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> যোগ করা হচ্ছে...';
    }
    
    fetch(`/api/add-to-cart/${productId}/`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
        },
    })
    .then(response => response.json())
    .then(data => {
        // Restore button
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-cart-plus"></i> Add Cart';
        }
        
        if (data.success) {
            // Update cart count in navbar
            const cartBadge = document.getElementById('cart-count-badge');
            if (cartBadge) {
                cartBadge.textContent = data.cart_total_items;
                cartBadge.style.display = 'inline-block';
            }
            
            // Show success toast
            showToast(
                'কার্টে যোগ হয়েছে!',
                `${data.product.title} (${data.product.unit}) - ৳${data.product.price}`
            );
        } else {
            showToast(
                'ত্রুটি!',
                data.error || 'কোনো সমস্যা হয়েছে। আবার চেষ্টা করুন।',
                'error'
            );
        }
    })
    .catch(error => {
        // Restore button
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-cart-plus"></i> Add Cart';
        }
        
        console.error('Error:', error);
        showToast(
            'সংযোগ ত্রুটি!',
            'সার্ভারের সাথে সংযোগ করতে পারা যায়নি।',
            'error'
        );
    });
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Find all "Add Cart" buttons and make them AJAX
    document.querySelectorAll('[data-add-to-cart]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.getAttribute('data-product-id');
            addToCartAjax(productId, e);
        });
    });
});
