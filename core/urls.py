from django.urls import path
from .views import (
    HomeView,
    checkout,
    products,
    ProductDetailView,
    add_to_cart,
    remove_from_cart,
    OrderSummaryView,
    remove_single_item_from_cart,
    BestSellerView
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('bestseller/', BestSellerView.as_view(), name='bestseller'),
    path('products/', products, name='products'),
    path('product/<slug>/', ProductDetailView.as_view(), name='product'),
    path('checkout/', checkout, name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('add-to-cart/<slug>', add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<slug>', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
]