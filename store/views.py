import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import * 
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.csrf import csrf_exempt
import datetime
from .utils import cookieCart, cartData, guestOrder
from .forms import NewComment
from django.contrib.auth.decorators import login_required 
# Create your views here.

def store(request):
    search = Product.objects.all()
    title = None
    if 'search_name' in request.GET:
        title = request.GET['search_name']
        if title: 
            search = search.filter(name__icontains=title)
    products = search

    if request.method == 'GET':
        min_price = request.GET.get('min', None)
        max_price = request.GET.get('max', None)
        if min_price and max_price:
            products = products.filter(price__gte=min_price, price__lte=max_price)
        elif min_price:
            products = products.filter(price__gte=min_price)
        elif max_price:
            products = products.filter(price__lte=max_price)

    categories = Category.objects.all()
    data = cartData(request)
    cartItems = data['cartItems']
    context = {'products': products, 'categories': categories, 'cartItems': cartItems}
    return render (request, 'store/pages/store.html', context)

def cart(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render (request, 'store/pages/cart.html', context)

@csrf_exempt
def checkout(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render (request, 'store/pages/checkout.html', context)

def updateItem(request): 
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']

    customer = request.user.customer
    product = Product.objects.get(id = productId) 
    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)
    if action == 'add':
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    orderItem.save()

    if orderItem.quantity <= 0 : 
        orderItem.delete()
    return JsonResponse('Item was added', safe= False)

@csrf_exempt
def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    print('data:', request.body)
    data = json.loads(request.body)
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        
    else:
        customer, order = guestOrder(request, data)
    total = float(data['form']['total'])
    order.transaction_id = transaction_id
    if total == order.get_cart_total:
        order.complete = True
    order.save()
    return JsonResponse('payment complete', safe= False)

def view_product(request, id):
    data = cartData(request)
    cartItems = data['cartItems']
    product = get_object_or_404(Product, pk=id)
    products = Product.objects.all
    comments = product.comments.filter(active=True)
    comment_form = NewComment() 
    new_commment = None
    items = data['items']
    context = {
        'product': product,
        'cartItems': cartItems,
        'products': products,
        'comments': comments,
        'comment_form': comment_form,
        'items': items,
    }
    if request.method == 'POST':
        comment_form = NewComment(data = request.POST)
        if comment_form.is_valid():
            new_commment = comment_form.save(commit=False)
            new_commment.product = product
            new_commment.save()
            comment_form = NewComment()
    else: 
        comment_form = NewComment()
    return render(request, 'store/pages/view_product.html', context)

def add_to_favorites(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.user.is_authenticated:
        user_customer = request.user.customer
        user_customer.favorite_products.add(product)
        return render(request, 'store/pages/store.html')
    
def favorite_product(request):
    if request.user.is_authenticated:
        user_customer = request.user.customer
        favorite_products = user_customer.favorite_products.all()
        print('favorite_products: ', favorite_products)
        return render(request, 'store/pages/favorite_product.html', {'favorite_products': favorite_products})

def remove_from_favorites(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    user_customer = request.user.customer
    user_customer.favorite_products.remove(product)
    favorite_products = user_customer.favorite_products.all()
    return render(request, 'store/pages/favorite_product.html', {'favorite_products': favorite_products})


@login_required(login_url='login')
def profile(request, id):
    data = cartData(request)
    cartItems = data['cartItems']
    context = {
        'cartItems': cartItems,
    }
    return render(request, 'store/pages/profile.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username = username, password = password)
        if user is not None: 
            print (user)
            login(request, user)
            return redirect('/')
        else: 
            messages.info(request, 'Credentials Invalid')
            print('Credentials Invalid')
            return redirect('login')
    else:
        return render (request, 'store/pages/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirmpassword = request.POST['confirmpassword']
        if password == confirmpassword:
            if User.objects.filter(email = email).exists():
                messages.info(request, 'Email Already Exists')
                print("Email Already Exists")
                return redirect('register')
            elif User.objects.filter(username = username).exists():
                messages.info(request, 'Username Already Exists')
                print("username Already Exists")
                return redirect('register')
            else: 
                user = User.objects.create_user(username = username, email = email, password = password)
                user.save()
                customer = Customer.objects.get_or_create(user = user, name = user.username, email = user.email)
                print("save new user")
                return redirect('login')
        else: 
            messages.info(request, 'Password Not The Same')
            print("password not the same")
            return redirect('register')
    else:
        return render(request, 'store/pages/register.html')    

def logout_view(request):
    logout(request)
    return redirect('/')

