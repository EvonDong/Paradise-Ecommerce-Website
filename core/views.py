from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile
from .models import CATEGORY_CHOICES
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
# from example.config import pagination

import stripe
import random
import string

stripe.api_key = "sk_test_4eC39HqLyjWDarjtT1zdp7dc"

# Create your views here.

# def home(request):
#     context = {
#         'items': Item.objects.all()
#     }
#     return render(request, "home-page.html", context)


# def checkout(request):
#     context = {
#         # 'items': Item.objects.all()
#     }
#     return render(request, "checkout-page.html", context)

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "product-page.html", context)

def get_categories():
    return CATEGORY_CHOICES

class HomeView(ListView):
    # def get(self, *args, **kwargs):
    #     self.object_list = Item.objects.filter(isBestseller=True)
    model = Item
    paginate_by = 5
    template_name = "home-page.html"

class BestSellerView(ListView):
    model = Item
    paginate_by = 8
    template_name = "bestseller.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = CATEGORY_CHOICES
        return context
    
    
def search(request):
    try:
        query = request.GET.get('q')
    except:
        query = None

    if query:
        results = Item.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))
        print(results)
        context = {
            'query': query,
            'results': results
        }
    
    # pages = pagination(request, results, num=1)
    # context = {
    #     'items': pages[0],
    #     'page_range': pages[1],
    #     'query': query
    # }

    return render(request, "search-page.html", context)

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'account/order_summary.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order! ):")
            return redirect("/")


class ProductDetailView(DetailView):
    model = Item
    template_name = "product-page.html"

def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)  # qs: : query set
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }
            shipping_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )
            if shipping_address_qs.exists():
                context.update({'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'B',
                default = True
            )
            if billing_address_qs.exists():
                context.update({'default_billing_address': billing_address_qs[0]})

            return render(self.request, "checkout-page.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order!")
            return redirect("/")  #core:checkout



    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:     #check if order  valid
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print("Using default shipping addr")
                    address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'S',
                        default = True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request, "No default shipping address has been registered in the system.")
                        return redirect('core:checkout')
                else:
                    print("User is creating new shipping address.")

                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    #TODO: add functionalities for these fields
                    # same_shipping_address = form.cleaned_data.get('same_shipping_address')
                    # save_info = form.cleaned_data.get('save_info')
                    
                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user = self.request.user,
                            street_address = shipping_address1,
                            apartment_address = shipping_address2,
                            country = shipping_country,
                            zip = shipping_zip,
                            address_type = 'S'
                        )
                        shipping_address.save()
                        
                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info("Please fill in the required shipping address fields.")



                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = "B"
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using default billing addr")
                    address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'B',
                        default = True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, "No default billing address has been registered in the system.")
                        return redirect('core:checkout')
                else:
                    print("User is creating new billing address.")

                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')
                    #TODO: add functionalities for these fields
                    # same_shipping_address = form.cleaned_data.get('same_shipping_address')
                    # save_info = form.cleaned_data.get('save_info')
                    
                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user = self.request.user,
                            street_address = billing_address1,
                            apartment_address = billing_address2,
                            country = billing_country,
                            zip = billing_zip,
                            address_type = 'B'
                        )
                        billing_address.save()
                        
                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info("Please fill in the required billing address fields.")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe') 
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request, "Checkout failed. Invalid payment option selected.")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order! ):")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *agrs, **kwargs):
        # order
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }

            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    #update context with default card
                    context.update({
                        'card': card_list[0]
                    })

            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "You have not added a billing address.")
            return redirect("core:checkout")
    
    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)

        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save_card = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save_card:
                #allow to fetch cards
                if not userprofile.stripe_customer_id: # check if have stripe customer id associated to profile
                    customer = stripe.Customer.create(    # first time saving info
                        email = self.request.user.email,
                        # source = token
                    )
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()
                else:     # if profile alr exists
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id,
                        customer.sources.create(source=token)
                    )

        # token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)

        try:
            if use_default or save_card:
                charge = stripe.Charge.create(     # have a profile
                    amount = amount,
                    currency = "usd",
                    customer=userprofile.stripe_customer_id
                )
            else:
                charge = stripe.Charge.create(    #make ~anonymous purchase
                    amount = amount,
                    currency = "usd",
                    source=token
                )

        # try:
        #     charge = stripe.Charge.create(
        #         amount=amount, # value is in cents
        #         currency="sgd",
        #         source=token
        #     )

            #create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            # assign payment to the order
            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, "Your order was successful.")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request, "Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request, "Something  went wrong. You were not charged. Pls try again.")
            return redirect("/")

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            #send email to ourselves
            messages.warning(self.request, "A serious error occured. We have been notified. ")
            return redirect("/")




@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        ordered=False,
        user=request.user
    )
    order_qs = Order.objects.filter(
        user=request.user, ordered=False)  # qs: : query set
    if order_qs.exists():
        order = order_qs[0]
        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item's quantity is updated!")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item is now added to your cart!")
            order.items.add(order_item)
            return redirect("core:product", slug=slug)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item is now added to your cart!")
    return redirect("core:product", slug=slug)


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user, ordered=False)  # qs: : query set
    if order_qs.exists():
        order = order_qs[0]
        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                ordered=False,
                user=request.user
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item is now removed from the cart!")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item is not in your cart!")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order!")
        return redirect("core:product", slug=slug)

    return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user, ordered=False)  # qs: : query set
    if order_qs.exists():
        order = order_qs[0]
        # Check if order item is in order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                ordered=False,
                user=request.user
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity is now updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item is not in your cart!")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order!")
        return redirect("core:product", slug=slug)

    return redirect("core:product", slug=slug)

def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)  
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "There is no such coupon!")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)  # qs: : query set
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon!")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order!")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')

            try:
                # edit the order
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request has been sent successfully.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist. Please check the order reference code.")
                return redirect("core:request-refund")
        
        else:
            messages.warning(self.request, "Form is invalid. Pls check if your email is correct.")
            return redirect("core:request-refund")

                