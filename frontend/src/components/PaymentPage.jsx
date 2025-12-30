import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, useStripe, useElements, CardElement } from '@stripe/react-stripe-js';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

// Load Stripe with your publishable key
const stripePromise = loadStripe('pk_test_your_stripe_publishable_key_here');

// Payment Form Component
const PaymentForm = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const stripe = useStripe();
  const elements = useElements();
  const { user, token } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!stripe || !elements) {
      // Stripe.js has not loaded yet
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Create a payment method
      const { error, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: elements.getElement(CardElement),
        billing_details: {
          email: user?.email || '',
        },
      });

      if (error) {
        setError(error.message);
        setLoading(false);
        return;
      }

      // Send payment method ID to your server to create a payment intent
      const response = await fetch('/api/payment/create-intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          payment_method_id: paymentMethod.id,
          amount: 100, // $1.00 in cents
          currency: 'usd',
          description: 'Pro Membership',
          email: user?.email
        }),
      });

      const result = await response.json();

      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }

      // Confirm the payment
      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(
        result.client_secret
      );

      if (confirmError) {
        setError(confirmError.message);
        setLoading(false);
        return;
      }

      // Payment succeeded
      if (paymentIntent.status === 'succeeded') {
        toast.success('Payment successful! Upgraded to Pro!');
        
        // Update user status to pro
        // In a real app, you would update the user's pro status here
        
        // Redirect to dashboard or success page
        window.location.href = '/dashboard';
      }
    } catch (err) {
      setError('An error occurred during payment processing');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Card element options
  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': {
          color: '#aab7c4',
        },
      },
      invalid: {
        color: '#9e2146',
      },
    },
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Card Details
          </label>
          <div className="border border-gray-300 rounded-lg p-3">
            <CardElement options={cardElementOptions} />
          </div>
        </div>

        {error && (
          <div className="text-red-600 text-sm mb-4">{error}</div>
        )}

        <button
          type="submit"
          disabled={!stripe || loading}
          className="btn btn-primary w-full"
        >
          {loading ? (
            <>
              <span className="loading-spinner mr-2"></span>
              Processing...
            </>
          ) : (
            'Pay $1.00 for Pro Membership'
          )}
        </button>
      </div>
    </form>
  );
};

// Payment Page Component
const PaymentPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upgrade to Pro</h1>
          <p className="text-gray-600">Unlock premium features with a $1 monthly subscription</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Pro Membership Benefits</h2>
            <ul className="space-y-2">
              <li className="flex items-center">
                <svg className="h-5 w-5 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>Unlimited API calls</span>
              </li>
              <li className="flex items-center">
                <svg className="h-5 w-5 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>Priority support</span>
              </li>
              <li className="flex items-center">
                <svg className="h-5 w-5 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>Advanced image processing</span>
              </li>
              <li className="flex items-center">
                <svg className="h-5 w-5 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>Access to all premium tools</span>
              </li>
            </ul>
          </div>

          <div className="border-t pt-6">
            <div className="flex justify-between items-center mb-4">
              <span className="text-gray-600">Pro Membership</span>
              <span className="font-semibold">$1.00</span>
            </div>
            <div className="flex justify-between items-center mb-6">
              <span className="text-gray-600">Total</span>
              <span className="text-lg font-bold text-indigo-600">$1.00</span>
            </div>

            <Elements stripe={stripePromise}>
              <PaymentForm />
            </Elements>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentPage;