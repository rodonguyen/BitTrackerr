import ccxt
import config
import supertrend_bot

account = ccxt.binance({
    "apiKey": config.API_BINANCE,
    "secret": config.SECRET_BINANCE,
})

bot_matic = supertrend_bot.SupertrendBot(
                account=account,
                coinpair='SOL/USDT',
                trade_log_path='log/trade_log_bot_matic.txt',
                length = 7, multiplier = 4.5,
                is_in_position=False, 
                position=0, 
                lot=50,
                timeframe='15m',
                timeframe_in_minutes=15)


bot_matic.run_forever()