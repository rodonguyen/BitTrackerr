from collections import namedtuple
import utils

from datetime import datetime
import time
import pandas as pd
pd.set_option('display.max_rows', None)



class SupertrendBot:
    def __init__(self, 
                account,
                coinpair,
                trade_log_path,
                length,
                multiplier,
                is_in_position=False, 
                position=0, 
                lot=50,
                timeframe='15m',
                timeframe_in_minutes=15    ):
        self.account = account
        self.coinpair = coinpair
        self.trade_log_path = trade_log_path
        self.is_in_position = is_in_position
        self.position = position
        self.lot = lot
        self.timeframe = timeframe
        self.timeframe_in_minutes = timeframe_in_minutes
        self.config = namedtuple('Supertrend_config', ['length', 'multiplier'])._make([length, multiplier])

        # Log start configuration
        utils.trade_log(f"\n\n\"Start config: is_in_position={is_in_position}," +
                        f"position={position}," +
                        f"lot={lot}," +
                        f"coinpair={coinpair}," +
                        f"timeframe_in_minutes={timeframe_in_minutes}," +
                        f"timeframe={timeframe}," +
                        f"{self.config}\"", 
                        trade_log_path)

    def __tr(self, data):
        '''Calculate true range'''
        data['previous_close'] = data['close'].shift(1)
        data['high-low'] = abs(data['high'] - data['low'])
        data['high-pc'] = abs(data['high'] - data['previous_close'])
        data['low-pc'] = abs(data['low'] - data['previous_close'])
        tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

        return tr


    def __atr(self, data):
        '''Calculate average true range'''
        data['tr'] = self.__tr(data)
        atr = data['tr'].rolling(self.config.length).mean()
        return atr


    def __supertrend_format(self, df):
        ''' Return the dataframe with supertrend (aka. is_up_trend) signal column '''

        hl2 = (df['high'] + df['low']) / 2
        df['atr'] = self.__atr(df)
        df['upperband'] = hl2 + (self.config.multiplier * df['atr'])
        df['lowerband'] = hl2 - (self.config.multiplier * df['atr'])
        df['is_uptrend'] = True

        for current in range(1, len(df.index)):
            previous = current - 1

            if df.loc[current,'close'] > df.loc[previous,'upperband']:
                df.loc[current,'is_uptrend'] = True
            elif df.loc[current,'close'] < df.loc[previous,'lowerband']:
                df.loc[current,'is_uptrend'] = False
            else:
                df.loc[current,'is_uptrend'] = df.loc[previous,'is_uptrend']
                if df.loc[current,'is_uptrend'] and df.loc[current,'lowerband'] < df.loc[previous,'lowerband']:
                    df.loc[current,'lowerband'] = df.loc[previous,'lowerband']
                if not df.loc[current,'is_uptrend'] and df.loc[current,'upperband'] > df.loc[previous,'upperband']:
                    df.loc[current,'upperband'] = df.loc[previous,'upperband']
        return df


    def __check_buy_sell_signals(self, supertrend_data):
        last_row_index = len(supertrend_data.index) - 1
        previous_row_index = last_row_index - 1

        # # Uncomment this to execute order immediately
        # df.loc[last_row_index,'is_uptrend'] = True
        # df.loc[previous_row_index,'is_uptrend'] = False

        if not supertrend_data.loc[previous_row_index,'is_uptrend'] and supertrend_data.loc[last_row_index,'is_uptrend']:
            if not self.is_in_position:
                self.position = self.lot / supertrend_data.loc[last_row_index,'close'] 
                order = self.account.create_market_buy_order(self.coinpair, self.position)
                self.position = order['filled']
                self.is_in_position = True
                utils.trade_log(f"Uptrend,Buy,{self.is_in_position},{self.position},", self.trade_log_path)
            else:
                utils.trade_log(f"Already in position,-,{self.is_in_position},{self.position},", self.trade_log_path)

        elif supertrend_data.loc[previous_row_index,'is_uptrend'] and not supertrend_data.loc[last_row_index,'is_uptrend']:
            if self.is_in_position:
                order = self.account.create_market_sell_order(self.coinpair, self.position)
                self.position = self.position - order['filled']
                self.is_in_position = False
                utils.trade_log(f"Downtrend,Sell,{self.is_in_position},{self.position},", self.trade_log_path)
            else:
                utils.trade_log(f"No position,-,{self.is_in_position},{self.position},", self.trade_log_path)
        
        else:
            utils.trade_log('No signal,,,,', self.trade_log_path)

    def run_once(self):
        utils.trade_log(f"\n{datetime.now()},", self.trade_log_path)

        bars = self.account.fetch_ohlcv(self.coinpair, self.timeframe, limit=200)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        supertrend_data = self.__supertrend_format(df)
        supertrend_data.drop(columns=['previous_close', 'high-low', 'high-pc', 'low-pc', 'tr', 'atr'], axis=0, inplace=True)
        print('\n', supertrend_data.tail(4), '\n')
        self.__check_buy_sell_signals(supertrend_data)

        utils.trade_log(f"{datetime.now()}", self.trade_log_path)

    def run_forever(self):
        little_delay = 5
        while True:
            try:
                self.run_once()
            except Exception as e:
                print(e)
                time.sleep(5)
                continue

            # time.sleep(2)         # for testing
            timeframe_in_seconds = 60*self.timeframe_in_minutes
            remaining_sleep_seconds_to_finish_the_timeframe = time.time() % (60*self.timeframe_in_minutes) 
            time.sleep(timeframe_in_seconds - remaining_sleep_seconds_to_finish_the_timeframe + little_delay)




