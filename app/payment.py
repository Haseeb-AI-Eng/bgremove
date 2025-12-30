import stripe
from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class PaymentIntentCreate(BaseModel):
    amount: int  # Amount in cents (so $1.00 = 100)
    currency: str = "usd"
    description: str
    email: str  # User's email

class SubscriptionCreate(BaseModel):
    email: str
    price_id: str  # Stripe Price ID for the subscription

# Create a payment intent for one-time payments (e.g. $1 for a feature)
def create_payment_intent(payment_data: PaymentIntentCreate) -> dict:
    try:
        intent = stripe.PaymentIntent.create(
            amount=payment_data.amount,  # Amount in cents (100 = $1.00)
            currency=payment_data.currency,
            description=payment_data.description,
            metadata={'email': payment_data.email}
        )
        return {
            'client_secret': intent.client_secret,
            'id': intent.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Create a subscription for pro membership
def create_subscription(subscription_data: SubscriptionCreate) -> dict:
    try:
        # In a real app, you would have predefined price IDs in Stripe dashboard
        # For demo purposes, I'm using a generic approach
        # You'll need to create actual products and prices in your Stripe dashboard
        
        # Create customer if doesn't exist
        customer = stripe.Customer.create(
            email=subscription_data.email,
            description=f"Pro member: {subscription_data.email}"
        )
        
        # Create subscription (you need to have a price_id in your Stripe dashboard)
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[
                {
                    'price': subscription_data.price_id,  # This needs to be a real price ID from Stripe
                }
            ],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent']
        )
        
        return {
            'id': subscription.id,
            'customer_id': customer.id,
            'status': subscription.status,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Verify payment/subscription status
def verify_payment_status(payment_id: str) -> dict:
    try:
        intent = stripe.PaymentIntent.retrieve(payment_id)
        return {
            'id': intent.id,
            'status': intent.status,
            'amount': intent.amount,
            'currency': intent.currency
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Create a simple pro plan using Stripe's approach
def create_pro_plan():
    """Create a $1 pro plan in Stripe - this needs to be done in the Stripe dashboard"""
    # This function describes what needs to be set up in Stripe dashboard
    # 1. Create a product in Stripe: "Pro Membership"
    # 2. Create a price: $1.00 recurring
    # 3. Use the price ID when creating subscriptions
    pass