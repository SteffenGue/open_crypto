#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains scripts to demonstrate the features of the application.

Classes:
 - Examples: Contains examples and illustrations to demonstrate all request methods.
"""
import os
import threading
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.pyplot import GridSpec
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

# noinspection PyUnresolvedReferences
import _paths  # pylint: disable=unused-import
from main import run as main_run
from model.database.tables import *
from export import database_session as get_session
from settings import Setting
from kill_switch import KillSwitch


class Examples:
    """
    Helper class providing examples and illustrations for all request methods.

    The respective configuration files are named according to the class-methods and can be found in the
    resources/configs folder. All requests are configured to terminate after a single run.
    """
    configuration_file: str
    plt.style.use("ggplot")
    pd.set_option("display.max_columns", None)

    @staticmethod
    def __start_catch_systemexit(configuration_file: str) -> None:
        try:
            main_run(configuration_file, os.getcwd())
        except SystemExit:
            return

    @staticmethod
    def __clear_database_table(session: Session, table: DatabaseTable) -> None:
        """
        Deletes all entries from a database table.
        @param session: SQLAlchemy-ORM Session.
        @param table: Database table
        """
        print("Clearing table: {}.".format(table.__name__))
        session.query(table).delete()
        session.commit()

    @staticmethod
    def static() -> plt.hist:
        """
        Request all available exchanges currency-pairs and create a histogram of their distribution.
        """
        configuration_file = 'Examples/static'
        session = get_session(configuration_file)

        Examples.__start_catch_systemexit(configuration_file)

        query = session.query(ExchangeCurrencyPairView)
        dataframe = pd.read_sql(query.statement, con=session.bind)

        dataframe.exchange_name.value_counts().hist(bins=len(set(dataframe.exchange_name)))
        plt.title("Traded Pairs on Exchanges")
        plt.ylabel("Number of Exchanges")
        plt.xlabel("Number of Traded Pairs")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def platforms() -> plt.plot:
        """
        Request BTC-USD data from the platform 'www.coingecko.com' and create a plot.
        """
        configuration_file = 'Examples/platform'

        Examples.__start_catch_systemexit(configuration_file)

        session = get_session(configuration_file)
        query = session.query(HistoricRateView).filter(HistoricRateView.exchange == 'COINGECKO',
                                                       HistoricRateView.first_currency == "BITCOIN",
                                                       HistoricRateView.second_currency == "USD")
        dataframe = pd.read_sql(query.statement, con=session.bind, index_col='time')
        dataframe.sort_index(inplace=True)

        fig = plt.figure(constrained_layout=True, figsize=(8, 6))
        grid_spec = GridSpec(4, 4, figure=fig)
        plt.rc('grid', linestyle=":", color='black')

        ax0 = fig.add_subplot(grid_spec[0:2, :])
        ax0.plot(dataframe.close, label="Close")
        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.title("Bitcoin Daily Close in US-Dollar")
        ax0.grid(True)

        ax1 = fig.add_subplot(grid_spec[2:3, :])
        ax1.bar(dataframe.volume[dataframe.volume < 150 * 1e9].index,
                dataframe.volume[dataframe.volume < 150 * 1e9] / 1e9, label="Volume")
        plt.setp(ax1.get_xticklabels(), visible=False)
        ax1.grid(True)
        ax1.set_ylabel("Billion")
        plt.title("Bitcoin Daily Volume in US-Dollar")

        ax2 = fig.add_subplot(grid_spec[3:4, :])
        ax2.plot((dataframe.market_cap.divide(dataframe.close, axis=0) / 1e6), label="Supply")
        ax2.grid(True)
        ax2.set_ylabel("Million")
        ax2.set_xlabel("Time (Daily)")
        plt.title("Bitcoin Total Coin Supply")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def historic_rates(timer: int = 60) -> plt.plot:
        """
        Request BTC-USD(T) data from several exchanges and plot them simultaneously.
        """

        configuration_file = 'Examples/historic'
        session = get_session(configuration_file)
        Examples.__clear_database_table(session, HistoricRate)
        thread = threading.Timer(timer, KillSwitch().kill)
        thread.start()
        Examples.__start_catch_systemexit(configuration_file)

        exchanges = ('BINANCE', 'BITTREX')
        session = get_session(configuration_file)
        query = session.query(HistoricRateView)
        query = query.filter(HistoricRateView.exchange.in_(exchanges))

        dataframe = pd.read_sql(query.statement, con=session.bind, index_col='time')
        dataframe = pd.pivot_table(dataframe, columns=dataframe.exchange, index=dataframe.index)
        dataframe = dataframe.close

        for column in dataframe.columns:
            plt.plot(dataframe.loc[:, column].dropna(), linestyle="dotted", linewidth=.5, label=column)
        plt.title("ETH/BTC - Minute Candles")
        plt.xlabel("Time")
        plt.ylabel("Price in US-Dollar")
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def trades() -> plt.plot:
        """
        Request ETH-BTC transaction data from Coinbase and plot the price series and trade direction.
        """
        configuration_file = 'Examples/trades'

        Examples.__start_catch_systemexit(configuration_file)

        exchange = "COINBASE"
        session = get_session(configuration_file)
        query = session.query(TradeView).filter(TradeView.exchange == exchange).\
            order_by(desc(TradeView.time)).limit(1000)

        dataframe = pd.read_sql(query.statement, con=session.bind, index_col='time')
        dataframe.sort_index(inplace=True)

        plt.plot(dataframe[dataframe.direction == "sell"].loc[:, "price"], linestyle="dotted",
                 color="red", label="Sells", linewidth=1.5)
        plt.plot(dataframe[dataframe.direction == "buy"].loc[:, "price"], linestyle="dotted",
                 color="green", label="Buys", linewidth=1.5)

        plt.xticks(rotation=45)
        plt.legend()
        plt.title("ETH/BTC Trades from Coinbase")
        plt.xlabel("Timestamp")
        plt.ylabel("Price in BTC")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def order_books() -> plt.plot:
        """
        Requests the current order-book snapshot from Coinbase and plot the market depth.
        """
        configuration_file = 'Examples/order_books'
        exchange = 'COINBASE'
        session = get_session(configuration_file)
        Examples.__start_catch_systemexit(configuration_file)

        (timestamp,) = session.query(func.max(OrderBookView.time)).first()
        query = session.query(OrderBookView).filter(OrderBookView.exchange == exchange,
                                                    OrderBookView.time == timestamp)
        dataframe = pd.read_sql(query.statement, con=session.bind, index_col='time')
        plt.step(dataframe.bids_price, dataframe.bids_amount.cumsum(), color='green', label='bids')
        plt.step(dataframe.asks_price, dataframe.asks_amount.cumsum(), color='red', label='asks')

        plt.ylim(ymin=0)
        plt.title("Market Depth BTC/USD(T)")
        plt.xlabel("Price in USD(T)")
        plt.ylabel("Accum. Size in BTC")
        plt.legend()
        plt.tight_layout()
        plt.show()

    @staticmethod
    def exchange_listings() -> plt.plot:
        """
        Collects historical data for 10 currency-pairs quoted against USD(T) and plots the amount of exchanges,
        each currency was listed on over time.
        """
        print("Warning: This example takes several minutes to complete.")
        configuration_file = 'Examples/exchange_listings'
        with Setting() as settings:
            settings.set("request_settings", 'min_return_tuples', 100)
            settings.set("request_settings", "interval_settings", "equal")
            Examples.__start_catch_systemexit(configuration_file)

        session = get_session(configuration_file)
        base_currencies = ('BTC', 'LINK', 'ETH', 'XRP', 'LTC', 'ATOM', 'ADA', 'XLM', 'BCH', 'DOGE')
        query = session.query(HistoricRateView.time,
                              HistoricRateView.exchange,
                              HistoricRateView.first_currency,
                              HistoricRateView.close).filter(HistoricRateView.first_currency.in_(base_currencies))
        dataframe = pd.read_sql(query.statement, con=session.bind, index_col="time")
        dataframe = pd.pivot_table(dataframe, columns=[dataframe.exchange, dataframe.first_currency],
                                   index=dataframe.index).close['2010-01-01':]

        for currency in base_currencies:
            temp = dataframe.loc[:, (slice(None), currency.upper())]
            temp = temp.resample("d").mean()
            temp = temp.resample("m").median()
            temp.count(axis=1).plot(label="/".join([currency, "USD(T)"]))

        plt.legend()
        plt.xlabel("Time (Monthly)")
        plt.ylabel("Number of Exchanges")
        plt.tight_layout()
        plt.show()
