#!/usr/bin/env python3
"""
Ultimate Telegram Crypto Price Alert Bot
Features: Trending coins, portfolio tracking, fear & greed index, multiple alert types,
charts, inline keyboards, and professional UI with all bells and whistles
"""

import json
import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = "8251911180:AAG0dGXnOwyXzTGA5-cdK2sUU_8H8GveH-Q"
ALERTS_FILE = "alerts_final.json"
PORTFOLIO_FILE = "portfolio_final.json"
PRICE_HISTORY_FILE = "price_history_final.json"
COINGECKO_API = "https://api.coingecko.com/api/v3"
FEAR_GREED_API = "https://api.alternative.me/fng"
CHECK_INTERVAL = 60

# Conversation states
PORTFOLIO_COIN, PORTFOLIO_AMOUNT = range(2)
ALERT_COIN, ALERT_TYPE, ALERT_VALUE = range(3)

# Language support with extended translations
LANGUAGES = {
    'en': {
        'welcome': '🤖 **Welcome to Advanced Crypto Alert Bot!**\n\n💎 Your personal crypto companion with trending coins, portfolio tracking, and smart alerts.\n\n✨ Features:\n• 📊 Real-time price tracking\n• 🔥 Trending coins\n• 💼 Portfolio management\n• 🔔 Smart price & percentage alerts\n• 😨 Fear & Greed Index\n• 📈 Price charts\n• 🌍 Global market data\n• 🌐 Multilingual support',
        'main_menu': '📊 **Main Menu** - Choose an option:',
        'commands': '''
📋 **Available Commands:**

💰 *Price & Market*
/price [coin] - Get current price & 24h info
/chart [coin] - View 7-day price chart
/trending - Top 7 trending coins
/market - Global market overview
/fear - Fear & Greed Index

📈 *Portfolio*
/portfolio - View your portfolio
/addcoin [coin] [amount] - Add to portfolio
/removecoin [coin] - Remove from portfolio
/portfoliovalue - Total portfolio value

🔔 *Alerts*
/alert [coin] [above/below] [price] - Price alert
/percentalert [coin] [up/down] [%] - Percentage change alert
/myalerts - Show all alerts
/deletealert [id] - Delete alert

⚙️ *Settings*
/language - Change language (EN/MY)
/help - Show this help
/start - Show main menu
        ''',
        'price_format': '💰 **{coin}** Price Information\n\n🔹 Current: **${price:,.2f}**\n🔹 24h Change: **{change_24h:+.2f}%** {change_emoji}\n🔹 1h Change: **{change_1h:+.2f}%**\n🔹 7d Change: **{change_7d:+.2f}%**\n🔹 24h High: **${high_24h:,.2f}**\n🔹 24h Low: **${low_24h:,.2f}**\n🔹 Market Cap: **${market_cap:,.0f}**\n🔹 24h Volume: **${volume_24h:,.0f}**',
        'trending_header': '🔥 **Top 7 Trending Coins**\n\n',
        'trending_item': '{rank}. **{coin}** - ${price:,.2f} ({change:+.2f}%)\n',
        'market_overview': '🌍 **Global Market Overview**\n\n🔹 Total Market Cap: **${market_cap:,.0f}**\n🔹 24h Volume: **${volume_24h:,.0f}**\n🔹 BTC Dominance: **{btc_dominance:.2f}%**\n🔹 ETH Dominance: **{eth_dominance:.2f}%**\n🔹 Active Cryptocurrencies: **{active_cryptos}**',
        'fear_greed': '😨 **Fear & Greed Index**\n\n🔹 Current Score: **{score}/100**\n🔹 Classification: **{classification}**\n🔹 Last Updated: **{timestamp}**\n\n{gauge}',
        'portfolio_empty': '📭 Your portfolio is empty.\n\nAdd coins with: /addcoin [coin] [amount]\n\nExample: /addcoin BTC 0.5',
        'portfolio_header': '💼 **Your Portfolio**\n\n',
        'portfolio_item': '{emoji} {coin}: {amount:.4f} (${value:,.2f})\n',
        'portfolio_total': '\n💰 **Total Value: ${total:,.2f}**\n📊 **24h Change: {change:+.2f}%**',
        'portfolio_added': '✅ Added {amount:.4f} {coin} to portfolio',
        'portfolio_removed': '✅ Removed {coin} from portfolio',
        'portfolio_not_found': '❌ {coin} not found in portfolio',
        'alert_set': '✅ **Price Alert Set!**\n\n🔹 Coin: {coin}\n🔹 Condition: {direction} ${price:,.0f}\n🔹 Alert ID: {id}\n\nYou will be notified when this condition is met.',
        'percent_alert_set': '✅ **Percentage Alert Set!**\n\n🔹 Coin: {coin}\n🔹 Condition: {direction} {percent}%\n🔹 Alert ID: {id}\n\nYou will be notified when this condition is met.',
        'alert_exists': '⚠️ Similar alert already exists',
        'no_alerts': '📭 You have no active alerts.\n\nSet one with:\n/alert BTC above 50000\n/percentalert ETH up 5',
        'alerts_header': '🔔 **Your Active Alerts**\n\n',
        'alert_item': '{id}. {coin} {direction} {value}',
        'alert_deleted': '✅ Alert deleted successfully',
        'alert_not_found': '❌ Alert not found',
        'triggered': '🚨 **ALERT TRIGGERED!**\n\n🔹 {coin}\n🔹 Current Price: **${price:,.2f}**\n🔹 Condition: {direction} ${threshold:,.0f}',
        'percent_triggered': '🚨 **ALERT TRIGGERED!**\n\n🔹 {coin}\n🔹 Current Price: **${price:,.2f}**\n🔹 24h Change: **{change:+.2f}%** {direction}',
        'error_price': '❌ Could not fetch price for {coin}.\n\nTry /trending for supported coins.',
        'error_format': '❌ Invalid format.\n\nExamples:\n/alert BTC above 50000\n/percentalert ETH up 5',
        'error_price_value': '❌ Invalid price value. Please use a number.',
        'language_changed': '✅ Language changed to English 🇬🇧',
        'invalid_command': '❌ Invalid command. Use /help for available commands.',
        'chart_generating': '📊 Generating chart...',
        'chart_ready': '📈 **7-day price chart for {coin}**',
        'chart_error': '❌ Could not generate chart. Not enough data.',
        'loading': '⏳ Loading...',
        'back': '◀️ Back',
        'refresh': '🔄 Refresh',
        'more_info': 'ℹ️ More Info',
    },
    'my': {
        'welcome': '🤖 **Advanced Crypto Alert Bot သို့ ကြိုးဆိုပါသည်!**\n\n💎 သင့်ရဲ့ ကိုယ်ပိုင် crypto companion ။\n\n✨ Features:\n• 📊 Real-time price tracking\n• 🔥 Trending coins\n• 💼 Portfolio management\n• 🔔 Smart price & percentage alerts\n• 😨 Fear & Greed Index\n• 📈 Price charts\n• 🌍 Global market data\n• 🌐 Multilingual support',
        'main_menu': '📊 **အဓိက မီနူး** - ရွေးချယ်ပါ:',
        'commands': '''
📋 **ရနိုင်သည့် အမိန့်များ:**

💰 *ဈေးနှုန်း & စျေးကွက်*
/price [coin] - လက်ရှိ ဈေးနှုန်း
/chart [coin] - 7-day price chart ကြည့်ပါ
/trending - အပေါ် 7 trending coins
/market - Global market overview
/fear - Fear & Greed Index

📈 *Portfolio*
/portfolio - သင့်ရဲ့ portfolio ကြည့်ပါ
/addcoin [coin] [amount] - Portfolio သို့ ထည့်ပါ
/removecoin [coin] - Portfolio မှ ဖြုတ်ပါ
/portfoliovalue - Total portfolio value

🔔 *Alerts*
/alert [coin] [above/below] [price] - ဈေးနှုန်း ခြင်း
/percentalert [coin] [up/down] [%] - Percentage change alert
/myalerts - ခြင်းများ ပြပါ
/deletealert [id] - ခြင်း ဖျက်ပါ

⚙️ *Settings*
/language - ဘာသာစကား ပြောင်းလဲပါ (EN/MY)
/help - ကူညီ ပြပါ
/start - အဓိက မီနူး ပြပါ
        ''',
        'price_format': '💰 **{coin}** ဈေးနှုန်း အချက်အလက်\n\n🔹 လက်ရှိ: **${price:,.2f}**\n🔹 24h ပြောင်းလဲ: **{change_24h:+.2f}%** {change_emoji}\n🔹 1h ပြောင်းလဲ: **{change_1h:+.2f}%**\n🔹 7d ပြောင်းလဲ: **{change_7d:+.2f}%**\n🔹 24h အမြင့်: **${high_24h:,.2f}**\n🔹 24h အနိမ့်: **${low_24h:,.2f}**\n🔹 Market Cap: **${market_cap:,.0f}**\n🔹 24h Volume: **${volume_24h:,.0f}**',
        'trending_header': '🔥 **အပေါ် 7 Trending Coins**\n\n',
        'trending_item': '{rank}. **{coin}** - ${price:,.2f} ({change:+.2f}%)\n',
        'market_overview': '🌍 **Global Market Overview**\n\n🔹 Total Market Cap: **${market_cap:,.0f}**\n🔹 24h Volume: **${volume_24h:,.0f}**\n🔹 BTC Dominance: **{btc_dominance:.2f}%**\n🔹 ETH Dominance: **{eth_dominance:.2f}%**\n🔹 Active Cryptocurrencies: **{active_cryptos}**',
        'fear_greed': '😨 **Fear & Greed Index**\n\n🔹 လက်ရှိ Score: **{score}/100**\n🔹 အခန်းအလယ်: **{classification}**\n🔹 နောက်ဆုံး အဆင့်မြှင့်တင်: **{timestamp}**\n\n{gauge}',
        'portfolio_empty': '📭 သင့်ရဲ့ portfolio သည် ကျည်ပါ။',
        'portfolio_header': '💼 **သင့်ရဲ့ Portfolio**\n\n',
        'portfolio_item': '{emoji} {coin}: {amount:.4f} (${value:,.2f})\n',
        'portfolio_total': '\n💰 **စုစုပေါင်း တန်ဖိုး: ${total:,.2f}**\n📊 **24h ပြောင်းလဲ: {change:+.2f}%**',
        'portfolio_added': '✅ {amount:.4f} {coin} ကို portfolio သို့ ထည့်ပြီးပါပြီ',
        'portfolio_removed': '✅ {coin} ကို portfolio မှ ဖြုတ်ပြီးပါပြီ',
        'portfolio_not_found': '❌ {coin} သည် portfolio တွင် မတွေ့ရှိပါ',
        'alert_set': '✅ **ဈေးနှုန်း ခြင်း သတ်မှတ်ပြီးပါပြီ!**\n\n🔹 Coin: {coin}\n🔹 အခြေအနေ: {direction} ${price:,.0f}\n🔹 Alert ID: {id}',
        'percent_alert_set': '✅ **Percentage Alert သတ်မှတ်ပြီးပါပြီ!**\n\n🔹 Coin: {coin}\n🔹 အခြေအနေ: {direction} {percent}%\n🔹 Alert ID: {id}',
        'alert_exists': '⚠️ အလားတူ ခြင်း ရှိပြီးသည်',
        'no_alerts': '📭 သင့်ရဲ့ ကျန်းမာ ခြင်းများ မရှိပါ',
        'alerts_header': '🔔 **သင့်ရဲ့ ကျန်းမာ ခြင်းများ**\n\n',
        'alert_item': '{id}. {coin} {direction} {value}',
        'alert_deleted': '✅ ခြင်း ဖျက်ပြီးပါပြီ',
        'alert_not_found': '❌ ခြင်း မတွေ့ရှိပါ',
        'triggered': '🚨 **ခြင်း အကျ!**\n\n🔹 {coin}\n🔹 လက်ရှိ ဈေးနှုန်း: **${price:,.2f}**\n🔹 အခြေအနေ: {direction} ${threshold:,.0f}',
        'percent_triggered': '🚨 **ခြင်း အကျ!**\n\n🔹 {coin}\n🔹 လက်ရှိ ဈေးနှုန်း: **${price:,.2f}**\n🔹 24h ပြောင်းလဲ: **{change:+.2f}%** {direction}',
        'error_price': '❌ {coin} အတွက် ဈေးနှုန်း ရယူမရပါ။',
        'error_format': '❌ မမှန်ကန်သော ပုံစံ။',
        'error_price_value': '❌ မမှန်ကန်သော ဈေးနှုန်း တန်ဖိုး။',
        'language_changed': '✅ ဘာသာစကား မြန်မာ သို့ ပြောင်းလဲပြီးပါပြီ 🇲🇲',
        'invalid_command': '❌ မမှန်ကန်သော အမိန့်။',
        'chart_generating': '📊 ဆွဲချခြင်း လုပ်ဆောင်နေ...',
        'chart_ready': '📈 **{coin} အတွက် 7-day price chart**',
        'chart_error': '❌ Chart ကို ပြုလုပ်မရပါ။',
        'loading': '⏳ အခြင်း မဆုံးခြင်း...',
        'back': '◀️ ပြန်သွားပါ',
        'refresh': '🔄 Refresh',
        'more_info': 'ℹ️ အပြည့်အစုံ အချက်အလက်',
    }
}

# User preferences
user_languages: Dict[int, str] = {}


class UltimateCryptoBot:
    def __init__(self):
        self.alerts: Dict[int, List[Dict]] = {}
        self.portfolio: Dict[int, Dict[str, float]] = {}
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}
        self.load_data()
        self.checked_alerts: set = set()
        self.coin_map = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'BNB': 'binancecoin', 'XRP': 'ripple',
            'ADA': 'cardano', 'SOL': 'solana', 'DOGE': 'dogecoin', 'POLKADOT': 'polkadot',
            'LITECOIN': 'litecoin', 'CARDANO': 'cardano', 'USDT': 'tether', 'USDC': 'usd-coin',
            'LINK': 'chainlink', 'MATIC': 'matic-network', 'AVAX': 'avalanche-2',
            'ATOM': 'cosmos', 'ARB': 'arbitrum', 'OP': 'optimism', 'NEAR': 'near',
            'APTOS': 'aptos', 'SUI': 'sui', 'PEPE': 'pepe', 'SHIB': 'shiba-inu',
        }

    def load_data(self):
        """Load all data from files"""
        if os.path.exists(ALERTS_FILE):
            try:
                with open(ALERTS_FILE, 'r') as f:
                    data = json.load(f)
                    self.alerts = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading alerts: {e}")
                self.alerts = {}

        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, 'r') as f:
                    data = json.load(f)
                    self.portfolio = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading portfolio: {e}")
                self.portfolio = {}

        if os.path.exists(PRICE_HISTORY_FILE):
            try:
                with open(PRICE_HISTORY_FILE, 'r') as f:
                    self.price_history = json.load(f)
            except Exception as e:
                logger.error(f"Error loading price history: {e}")
                self.price_history = {}

    def save_data(self):
        """Save all data to files"""
        try:
            with open(ALERTS_FILE, 'w') as f:
                json.dump(self.alerts, f, indent=2)
            with open(PORTFOLIO_FILE, 'w') as f:
                json.dump(self.portfolio, f, indent=2)
            with open(PRICE_HISTORY_FILE, 'w') as f:
                json.dump(self.price_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def get_crypto_price(self, coin_symbol: str) -> Optional[Dict]:
        """Fetch cryptocurrency price and market data from CoinGecko API"""
        try:
            coin_id = self.coin_map.get(coin_symbol.upper(), coin_symbol.lower())
            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_1hr_change': 'true',
                'include_7d_change': 'true',
                'include_high_low_24h': 'true',
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if coin_id in data:
                coin_data = data[coin_id]
                return {
                    'price': coin_data.get('usd', 0),
                    'market_cap': coin_data.get('usd_market_cap', 0),
                    'volume_24h': coin_data.get('usd_24h_vol', 0),
                    'change_24h': coin_data.get('usd_24h_change', 0),
                    'change_1h': coin_data.get('usd_1h_change', 0),
                    'change_7d': coin_data.get('usd_7d_change', 0),
                    'high_24h': coin_data.get('usd_high_24h', 0),
                    'low_24h': coin_data.get('usd_low_24h', 0),
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {coin_symbol}: {e}")
            return None

    def get_trending_coins(self) -> Optional[List[Dict]]:
        """Get top 7 trending coins"""
        try:
            url = f"{COINGECKO_API}/search/trending"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            trending = []
            for item in data.get('coins', [])[:7]:
                coin = item['item']
                trending.append({
                    'name': coin['name'],
                    'symbol': coin['symbol'].upper(),
                    'price': coin.get('data', {}).get('price', 0),
                    'change_24h': coin.get('data', {}).get('price_change_percentage_24h', {}).get('usd', 0),
                    'thumb': coin.get('thumb', ''),
                })
            return trending
        except Exception as e:
            logger.error(f"Error fetching trending coins: {e}")
            return None

    def get_market_overview(self) -> Optional[Dict]:
        """Get global market data"""
        try:
            url = f"{COINGECKO_API}/global"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()['data']

            return {
                'market_cap': data.get('total_market_cap', {}).get('usd', 0),
                'volume_24h': data.get('total_volume', {}).get('usd', 0),
                'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
                'eth_dominance': data.get('market_cap_percentage', {}).get('eth', 0),
                'active_cryptos': data.get('active_cryptocurrencies', 0),
            }
        except Exception as e:
            logger.error(f"Error fetching market overview: {e}")
            return None

    def get_fear_greed_index(self) -> Optional[Dict]:
        """Get Fear & Greed Index"""
        try:
            response = requests.get(FEAR_GREED_API, timeout=5)
            response.raise_for_status()
            data = response.json()['data'][0]

            score = int(data['value'])
            if score < 25:
                classification = "Extreme Fear 😱"
            elif score < 45:
                classification = "Fear 😟"
            elif score < 55:
                classification = "Neutral 😐"
            elif score < 75:
                classification = "Greed 😊"
            else:
                classification = "Extreme Greed 🤑"

            return {
                'score': score,
                'classification': classification,
                'timestamp': data.get('timestamp', ''),
            }
        except Exception as e:
            logger.error(f"Error fetching fear & greed index: {e}")
            return None

    def record_price(self, coin: str, price: float):
        """Record price for history"""
        if coin not in self.price_history:
            self.price_history[coin] = []
        self.price_history[coin].append([time.time(), price])
        # Keep only last 7 days
        cutoff = time.time() - (7 * 24 * 60 * 60)
        self.price_history[coin] = [[t, p] for t, p in self.price_history[coin] if t > cutoff]

    def generate_price_chart(self, coin: str) -> Optional[BytesIO]:
        """Generate a 7-day price chart"""
        try:
            if coin not in self.price_history or len(self.price_history[coin]) < 2:
                return None

            data = self.price_history[coin]
            timestamps = [datetime.fromtimestamp(t) for t, _ in data]
            prices = [p for _, p in data]

            plt.figure(figsize=(10, 6), facecolor='#1a1a2e')
            ax = plt.gca()
            ax.set_facecolor('#0f3460')

            ax.plot(timestamps, prices, linewidth=2.5, color='#00d4ff', marker='o', markersize=4)
            ax.fill_between(timestamps, prices, alpha=0.3, color='#00d4ff')

            ax.set_title(f'{coin} - 7 Day Price Chart', fontsize=14, color='white', fontweight='bold')
            ax.set_xlabel('Time', fontsize=10, color='white')
            ax.set_ylabel('Price (USD)', fontsize=10, color='white')

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.xticks(rotation=45, color='white')
            plt.yticks(color='white')

            ax.grid(True, alpha=0.2, color='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format='png', facecolor='#1a1a2e', dpi=100)
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            logger.error(f"Error generating chart for {coin}: {e}")
            return None

    def add_alert(self, user_id: int, coin: str, alert_type: str, value1: float, value2: Optional[float] = None) -> Tuple[bool, int]:
        """Add a new alert for user"""
        if user_id not in self.alerts:
            self.alerts[user_id] = []

        alert_id = max([a['id'] for a in self.alerts[user_id]], default=0) + 1

        alert = {
            'id': alert_id,
            'coin': coin.upper(),
            'type': alert_type,
            'value': value1,
            'value2': value2,
            'created_at': datetime.now().isoformat(),
            'triggered': False
        }

        self.alerts[user_id].append(alert)
        self.save_data()
        return True, alert_id

    def get_user_alerts(self, user_id: int) -> List[Dict]:
        """Get all alerts for a user"""
        return self.alerts.get(user_id, [])

    def delete_alert(self, user_id: int, alert_id: int) -> bool:
        """Delete an alert"""
        if user_id in self.alerts:
            self.alerts[user_id] = [a for a in self.alerts[user_id] if a['id'] != alert_id]
            self.save_data()
            return True
        return False

    def add_portfolio_coin(self, user_id: int, coin: str, amount: float) -> bool:
        """Add or update coin in portfolio"""
        if user_id not in self.portfolio:
            self.portfolio[user_id] = {}

        coin_upper = coin.upper()
        if coin_upper in self.portfolio[user_id]:
            self.portfolio[user_id][coin_upper] += amount
        else:
            self.portfolio[user_id][coin_upper] = amount

        self.save_data()
        return True

    def remove_portfolio_coin(self, user_id: int, coin: str) -> bool:
        """Remove coin from portfolio"""
        if user_id in self.portfolio:
            coin_upper = coin.upper()
            if coin_upper in self.portfolio[user_id]:
                del self.portfolio[user_id][coin_upper]
                self.save_data()
                return True
        return False

    def get_portfolio(self, user_id: int) -> Dict[str, float]:
        """Get user's portfolio"""
        return self.portfolio.get(user_id, {})

    def get_portfolio_value(self, user_id: int) -> Tuple[float, Dict[str, float], float]:
        """Calculate total portfolio value and 24h change"""
        portfolio = self.get_portfolio(user_id)
        total_value = 0
        total_change_24h = 0
        values = {}

        for coin, amount in portfolio.items():
            price_data = self.get_crypto_price(coin)
            if price_data:
                value = amount * price_data['price']
                values[coin] = value
                total_value += value
                total_change_24h += (value * price_data['change_24h']) / 100

        avg_change = (total_change_24h / total_value * 100) if total_value > 0 else 0
        return total_value, values, avg_change

    def get_language(self, user_id: int) -> str:
        """Get user's language preference"""
        return user_languages.get(user_id, 'en')

    def set_language(self, user_id: int, language: str):
        """Set user's language preference"""
        if language in LANGUAGES:
            user_languages[user_id] = language

    def get_text(self, user_id: int, key: str) -> str:
        """Get translated text for user"""
        language = self.get_language(user_id)
        return LANGUAGES[language].get(key, LANGUAGES['en'].get(key, ''))

    def get_emoji_for_coin(self, coin: str) -> str:
        """Get emoji for coin"""
        emojis = {
            'BTC': '₿', 'ETH': 'Ξ', 'BNB': '🔶', 'XRP': '🌊', 'ADA': '♠️',
            'SOL': '☀️', 'DOGE': '🐕', 'POLKADOT': '🔴', 'LITECOIN': '🪙',
            'USDT': '💵', 'USDC': '💵', 'LINK': '🔗', 'MATIC': '🟣',
            'PEPE': '🐸', 'SHIB': '🐕', 'NEAR': '🌐', 'APTOS': '🚀',
        }
        return emojis.get(coin.upper(), '💰')


# Global bot instance
bot_instance = UltimateCryptoBot()


def create_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("💰 Price", callback_data="menu_price"),
            InlineKeyboardButton("🔥 Trending", callback_data="menu_trending"),
        ],
        [
            InlineKeyboardButton("📊 Market", callback_data="menu_market"),
            InlineKeyboardButton("😨 Fear Index", callback_data="menu_fear"),
        ],
        [
            InlineKeyboardButton("💼 Portfolio", callback_data="menu_portfolio"),
            InlineKeyboardButton("🔔 Alerts", callback_data="menu_alerts"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton("ℹ️ Help", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    user_id = update.effective_user.id
    welcome_text = bot_instance.get_text(user_id, 'welcome')
    menu_text = bot_instance.get_text(user_id, 'main_menu')

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text(
        menu_text,
        reply_markup=create_main_keyboard(user_id),
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command handler"""
    user_id = update.effective_user.id
    commands_text = bot_instance.get_text(user_id, 'commands')
    await update.message.reply_text(commands_text, parse_mode=ParseMode.MARKDOWN)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get detailed price information"""
    user_id = update.effective_user.id

    if not context.args or len(context.args) == 0:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()
    price_data = bot_instance.get_crypto_price(coin)

    if price_data is None:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin=coin)
        await update.message.reply_text(error_text)
        return

    bot_instance.record_price(coin, price_data['price'])

    change_emoji = "📈" if price_data['change_24h'] >= 0 else "📉"

    price_text = bot_instance.get_text(user_id, 'price_format').format(
        coin=coin,
        price=price_data['price'],
        change_24h=price_data['change_24h'],
        change_emoji=change_emoji,
        change_1h=price_data['change_1h'],
        change_7d=price_data['change_7d'],
        high_24h=price_data['high_24h'],
        low_24h=price_data['low_24h'],
        market_cap=price_data['market_cap'],
        volume_24h=price_data['volume_24h'],
    )

    keyboard = [
        [InlineKeyboardButton("📈 Chart", callback_data=f"chart_{coin}"),
         InlineKeyboardButton("🔔 Alert", callback_data=f"alert_{coin}")],
        [InlineKeyboardButton("◀️ Back", callback_data="menu_back")]
    ]

    await update.message.reply_text(
        price_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and show price chart"""
    user_id = update.effective_user.id

    if not context.args or len(context.args) == 0:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()
    loading_text = bot_instance.get_text(user_id, 'chart_generating')
    msg = await update.message.reply_text(loading_text)

    # Fetch some price data to populate history
    for _ in range(5):
        price_data = bot_instance.get_crypto_price(coin)
        if price_data:
            bot_instance.record_price(coin, price_data['price'])
        await asyncio.sleep(0.5)

    chart_buffer = bot_instance.generate_price_chart(coin)

    if not chart_buffer:
        error_text = bot_instance.get_text(user_id, 'chart_error')
        await msg.edit_text(error_text)
        return

    chart_text = bot_instance.get_text(user_id, 'chart_ready').format(coin=coin)
    await msg.delete()
    await update.message.reply_photo(
        photo=chart_buffer,
        caption=chart_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show trending coins"""
    user_id = update.effective_user.id
    loading_text = bot_instance.get_text(user_id, 'loading')
    
    msg = await update.message.reply_text(loading_text)

    trending_coins = bot_instance.get_trending_coins()

    if not trending_coins:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin="trending")
        await msg.edit_text(error_text)
        return

    header_text = bot_instance.get_text(user_id, 'trending_header')
    item_template = bot_instance.get_text(user_id, 'trending_item')

    message = header_text
    for rank, coin in enumerate(trending_coins, 1):
        item = item_template.format(
            rank=rank,
            coin=coin['symbol'],
            price=coin['price'],
            change=coin['change_24h']
        )
        message += item

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
    await msg.edit_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show global market overview"""
    user_id = update.effective_user.id
    loading_text = bot_instance.get_text(user_id, 'loading')
    
    msg = await update.message.reply_text(loading_text)

    market_data = bot_instance.get_market_overview()

    if not market_data:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin="market")
        await msg.edit_text(error_text)
        return

    market_text = bot_instance.get_text(user_id, 'market_overview').format(
        market_cap=market_data['market_cap'],
        volume_24h=market_data['volume_24h'],
        btc_dominance=market_data['btc_dominance'],
        eth_dominance=market_data['eth_dominance'],
        active_cryptos=market_data['active_cryptos'],
    )

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
    await msg.edit_text(
        market_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def fear_greed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Fear & Greed Index"""
    user_id = update.effective_user.id
    loading_text = bot_instance.get_text(user_id, 'loading')
    
    msg = await update.message.reply_text(loading_text)

    fg_data = bot_instance.get_fear_greed_index()

    if not fg_data:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin="fear")
        await msg.edit_text(error_text)
        return

    score = fg_data['score']
    gauge = "█" * (score // 5) + "░" * ((100 - score) // 5)

    fg_text = bot_instance.get_text(user_id, 'fear_greed').format(
        score=score,
        classification=fg_data['classification'],
        timestamp=fg_data['timestamp'],
        gauge=gauge,
    )

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
    await msg.edit_text(
        fg_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's portfolio"""
    user_id = update.effective_user.id
    portfolio = bot_instance.get_portfolio(user_id)

    if not portfolio:
        empty_text = bot_instance.get_text(user_id, 'portfolio_empty')
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await update.message.reply_text(empty_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    total_value, values, change_24h = bot_instance.get_portfolio_value(user_id)

    header_text = bot_instance.get_text(user_id, 'portfolio_header')
    item_template = bot_instance.get_text(user_id, 'portfolio_item')
    total_template = bot_instance.get_text(user_id, 'portfolio_total')

    message = header_text
    for coin, amount in portfolio.items():
        emoji = bot_instance.get_emoji_for_coin(coin)
        value = values.get(coin, 0)
        item = item_template.format(
            emoji=emoji,
            coin=coin,
            amount=amount,
            value=value
        )
        message += item

    message += total_template.format(total=total_value, change=change_24h)
    
    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add coin to portfolio"""
    user_id = update.effective_user.id

    if len(context.args) < 2:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()
    try:
        amount = float(context.args[1])
    except ValueError:
        error_text = bot_instance.get_text(user_id, 'error_price_value')
        await update.message.reply_text(error_text)
        return

    price_data = bot_instance.get_crypto_price(coin)
    if price_data is None:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin=coin)
        await update.message.reply_text(error_text)
        return

    bot_instance.add_portfolio_coin(user_id, coin, amount)
    added_text = bot_instance.get_text(user_id, 'portfolio_added').format(
        amount=amount,
        coin=coin
    )
    await update.message.reply_text(added_text)


async def remove_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove coin from portfolio"""
    user_id = update.effective_user.id

    if not context.args:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()

    if bot_instance.remove_portfolio_coin(user_id, coin):
        removed_text = bot_instance.get_text(user_id, 'portfolio_removed').format(coin=coin)
        await update.message.reply_text(removed_text)
    else:
        not_found_text = bot_instance.get_text(user_id, 'portfolio_not_found').format(coin=coin)
        await update.message.reply_text(not_found_text)


async def portfolio_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show total portfolio value"""
    user_id = update.effective_user.id
    total_value, _, change_24h = bot_instance.get_portfolio_value(user_id)
    
    if total_value == 0:
        empty_text = bot_instance.get_text(user_id, 'portfolio_empty')
        await update.message.reply_text(empty_text)
    else:
        change_emoji = "📈" if change_24h >= 0 else "📉"
        value_text = f"💰 **Total Portfolio Value: ${total_value:,.2f}**\n\n📊 **24h Change: {change_24h:+.2f}%** {change_emoji}"
        await update.message.reply_text(value_text, parse_mode=ParseMode.MARKDOWN)


async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a price alert"""
    user_id = update.effective_user.id

    if len(context.args) < 3:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()
    direction = context.args[1].lower()

    if direction not in ['above', 'below']:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    try:
        price_threshold = float(context.args[2])
    except ValueError:
        error_text = bot_instance.get_text(user_id, 'error_price_value')
        await update.message.reply_text(error_text)
        return

    price_data = bot_instance.get_crypto_price(coin)
    if price_data is None:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin=coin)
        await update.message.reply_text(error_text)
        return

    alert_type = f"price_{direction}"
    success, alert_id = bot_instance.add_alert(user_id, coin, alert_type, price_threshold)

    if success:
        alert_text = bot_instance.get_text(user_id, 'alert_set').format(
            coin=coin,
            direction=direction,
            price=price_threshold,
            id=alert_id
        )
        await update.message.reply_text(alert_text, parse_mode=ParseMode.MARKDOWN)
    else:
        exists_text = bot_instance.get_text(user_id, 'alert_exists')
        await update.message.reply_text(exists_text)


async def set_percent_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a percentage change alert"""
    user_id = update.effective_user.id

    if len(context.args) < 3:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    coin = context.args[0].upper()
    direction = context.args[1].lower()

    if direction not in ['up', 'down']:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    try:
        percent = float(context.args[2])
    except ValueError:
        error_text = bot_instance.get_text(user_id, 'error_price_value')
        await update.message.reply_text(error_text)
        return

    price_data = bot_instance.get_crypto_price(coin)
    if price_data is None:
        error_text = bot_instance.get_text(user_id, 'error_price').format(coin=coin)
        await update.message.reply_text(error_text)
        return

    alert_type = f"percent_{direction}"
    success, alert_id = bot_instance.add_alert(user_id, coin, alert_type, percent, price_data['price'])

    if success:
        alert_text = bot_instance.get_text(user_id, 'percent_alert_set').format(
            coin=coin,
            direction=direction,
            percent=percent,
            id=alert_id
        )
        await update.message.reply_text(alert_text, parse_mode=ParseMode.MARKDOWN)
    else:
        exists_text = bot_instance.get_text(user_id, 'alert_exists')
        await update.message.reply_text(exists_text)


async def my_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's active alerts"""
    user_id = update.effective_user.id
    alerts = bot_instance.get_user_alerts(user_id)

    if not alerts:
        no_alerts_text = bot_instance.get_text(user_id, 'no_alerts')
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await update.message.reply_text(no_alerts_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    header_text = bot_instance.get_text(user_id, 'alerts_header')
    alert_item_template = bot_instance.get_text(user_id, 'alert_item')

    message = header_text
    for alert in alerts:
        if alert['type'].startswith('price_'):
            direction = alert['type'].split('_')[1]
            value = f"${alert['value']:,.0f}"
        else:
            direction = alert['type'].split('_')[1]
            value = f"{alert['value']}%"

        item = alert_item_template.format(
            id=alert['id'],
            coin=alert['coin'],
            direction=direction,
            value=value
        )
        message += item + '\n'

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete an alert"""
    user_id = update.effective_user.id

    if not context.args:
        error_text = bot_instance.get_text(user_id, 'error_format')
        await update.message.reply_text(error_text)
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        error_text = bot_instance.get_text(user_id, 'error_price_value')
        await update.message.reply_text(error_text)
        return

    if bot_instance.delete_alert(user_id, alert_id):
        deleted_text = bot_instance.get_text(user_id, 'alert_deleted')
        await update.message.reply_text(deleted_text)
    else:
        not_found_text = bot_instance.get_text(user_id, 'alert_not_found')
        await update.message.reply_text(not_found_text)


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change language"""
    user_id = update.effective_user.id
    current_lang = bot_instance.get_language(user_id)

    new_lang = 'my' if current_lang == 'en' else 'en'
    bot_instance.set_language(user_id, new_lang)

    changed_text = bot_instance.get_text(user_id, 'language_changed')
    await update.message.reply_text(changed_text)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data == "menu_back":
        menu_text = bot_instance.get_text(user_id, 'main_menu')
        await query.edit_message_text(
            menu_text,
            reply_markup=create_main_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "menu_price":
        await query.edit_message_text("💰 Send /price [coin] to get price info")
    elif data == "menu_trending":
        await trending(update, context)
    elif data == "menu_market":
        await market(update, context)
    elif data == "menu_fear":
        await fear_greed(update, context)
    elif data == "menu_portfolio":
        await portfolio(update, context)
    elif data == "menu_alerts":
        await my_alerts(update, context)
    elif data == "menu_help":
        help_text = bot_instance.get_text(user_id, 'commands')
        await query.edit_message_text(help_text, parse_mode=ParseMode.MARKDOWN)
    elif data == "menu_settings":
        settings_text = "⚙️ **Settings**\n\n/language - Change language (EN/MY)"
        await query.edit_message_text(settings_text, parse_mode=ParseMode.MARKDOWN)
    elif data.startswith("chart_"):
        coin = data.split("_")[1]
        await chart(update, context)
    elif data.startswith("alert_"):
        coin = data.split("_")[1]
        alert_text = f"💰 Send /alert {coin} [above/below] [price] to set alert"
        await query.edit_message_text(alert_text)


async def check_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check all alerts and send notifications"""
    try:
        for user_id, alerts in bot_instance.alerts.items():
            for alert in alerts:
                if alert['triggered']:
                    continue

                coin = alert['coin']
                price_data = bot_instance.get_crypto_price(coin)

                if price_data is None:
                    continue

                alert_key = f"{user_id}_{alert['id']}"
                should_trigger = False
                direction_text = ""

                if alert['type'] == 'price_above' and price_data['price'] >= alert['value']:
                    should_trigger = True
                    direction_text = f"above ${alert['value']:,.0f}"
                elif alert['type'] == 'price_below' and price_data['price'] <= alert['value']:
                    should_trigger = True
                    direction_text = f"below ${alert['value']:,.0f}"
                elif alert['type'] == 'percent_up' and price_data['change_24h'] >= alert['value']:
                    should_trigger = True
                    direction_text = f"up {alert['value']}%"
                elif alert['type'] == 'percent_down' and price_data['change_24h'] <= -alert['value']:
                    should_trigger = True
                    direction_text = f"down {alert['value']}%"

                if should_trigger and alert_key not in bot_instance.checked_alerts:
                    bot_instance.checked_alerts.add(alert_key)
                    alert['triggered'] = True
                    bot_instance.save_data()

                    if alert['type'].startswith('price_'):
                        triggered_text = bot_instance.get_text(user_id, 'triggered').format(
                            coin=coin,
                            price=price_data['price'],
                            direction=direction_text.split()[0],
                            threshold=alert['value']
                        )
                    else:
                        triggered_text = bot_instance.get_text(user_id, 'percent_triggered').format(
                            coin=coin,
                            price=price_data['price'],
                            change=price_data['change_24h'],
                            direction=direction_text
                        )

                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=triggered_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Error sending alert to {user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_alerts: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("chart", chart))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("market", market))
    application.add_handler(CommandHandler("fear", fear_greed))
    application.add_handler(CommandHandler("portfolio", portfolio))
    application.add_handler(CommandHandler("addcoin", add_coin))
    application.add_handler(CommandHandler("removecoin", remove_coin))
    application.add_handler(CommandHandler("portfoliovalue", portfolio_value))
    application.add_handler(CommandHandler("alert", set_alert))
    application.add_handler(CommandHandler("percentalert", set_percent_alert))
    application.add_handler(CommandHandler("myalerts", my_alerts))
    application.add_handler(CommandHandler("deletealert", delete_alert))
    application.add_handler(CommandHandler("language", language))

    # Add callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Add error handler
    application.add_error_handler(error_handler)

    # Setup scheduler for price checking
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_alerts,
        "interval",
        seconds=CHECK_INTERVAL,
        args=[application],
        id="check_alerts",
        name="Check crypto alerts every minute",
        replace_existing=True,
    )
    application.scheduler = scheduler

    logger.info("Starting ultimate bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
