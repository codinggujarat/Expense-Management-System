import requests
import streamlit as st
from typing import Optional, List, Dict
import os

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_countries_and_currencies() -> Optional[List[Dict]]:
    """Fetch countries and their currencies from REST Countries API"""
    try:
        response = requests.get(
            "https://restcountries.com/v3.1/all?fields=name,currencies",
            timeout=10
        )
        response.raise_for_status()
        
        countries = response.json()
        processed_countries = []
        
        for country in countries:
            if country.get('currencies'):
                processed_countries.append({
                    'name': country['name']['common'],
                    'currencies': country['currencies']
                })
        
        return processed_countries
        
    except requests.RequestException as e:
        st.error(f"Failed to fetch countries data: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing countries data: {e}")
        return None

@st.cache_data(ttl=900)  # Cache for 15 minutes
def get_exchange_rates(base_currency: str) -> Optional[Dict]:
    """Fetch exchange rates for a base currency"""
    try:
        response = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{base_currency}",
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('rates', {})
        
    except requests.RequestException as e:
        st.error(f"Failed to fetch exchange rates: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing exchange rates: {e}")
        return None

def convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    """Convert amount from one currency to another"""
    if from_currency == to_currency:
        return amount
    
    # Get exchange rates with base currency as from_currency
    rates = get_exchange_rates(from_currency)
    
    if rates and to_currency in rates:
        converted_amount = amount * rates[to_currency]
        return round(converted_amount, 2)
    
    return None

def format_currency(amount: float, currency: str) -> str:
    """Format currency with proper symbol and formatting"""
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CAD': 'C$',
        'AUD': 'A$',
        'CHF': 'CHF',
        'CNY': '¥',
        'INR': '₹'
    }
    
    symbol = currency_symbols.get(currency, currency + ' ')
    return f"{symbol}{amount:,.2f}"

def get_popular_currencies() -> List[str]:
    """Get list of popular currencies"""
    return [
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 
        'SEK', 'NZD', 'MXN', 'SGD', 'HKD', 'NOK', 'INR', 'KRW'
    ]
