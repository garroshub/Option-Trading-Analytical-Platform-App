# -*- coding: utf-8 -*-
"""
@author: Garros

"""
import requests                  # [handles the http interactions](http://docs.python-requests.org/en/master/) 
from bs4 import BeautifulSoup    # beautiful soup handles the html to text conversion and more
import re                        # regular expressions are necessary for finding the crumb (more on crumbs later)
from datetime import datetime    # string to datetime object conversion
from time import mktime          # mktime transforms datetime objects to unix timestamps
import pandas as pd
from urllib.request import urlopen  
from io import StringIO
import json

# Stock Data
def get_crumbs_and_cookies(stock):
    """
    get crumb and cookies for historical data csv download from yahoo finance
    parameters: stock - short-handle identifier of the company 
    returns a tuple of header, crumb and cookie
    """
    
    url = 'https://finance.yahoo.com/quote/{}/history'.format(stock)
    with requests.session():
        header = {'Connection': 'keep-alive',
                   'Expires': '-1',
                   'Upgrade-Insecure-Requests': '1',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                   AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                   }
        
        website = requests.get(url, headers=header)
        # soup = BeautifulSoup(website.text, 'lxml')
        soup = BeautifulSoup(website.text)
        crumb = re.findall('"CrumbStore":{"crumb":"(.+?)"}', str(soup))

        return (header, crumb[0], website.cookies)

def convert_to_unix(date):
    """
    converts date to unix timestamp
    parameters: date - in format (dd-mm-yyyy)
    returns integer unix timestamp
    """
    datum = datetime.strptime(date, '%d-%m-%Y')
    
    return int(mktime(datum.timetuple())) + 86400 #adding 1 day due to timezone issue


def fnYFinHist(stock, interval='1d', day_begin='01-01-2013', day_end='17-11-2021'):
    """
    queries yahoo finance api to receive historical data in csv file format
    
    parameters: 
        stock - short-handle identifier of the company
        interval - 1d, 1wk, 1mo - daily, weekly monthly data
        day_begin - starting date for the historical data (format: dd-mm-yyyy)
        day_end - final date of the data (format: dd-mm-yyyy)
    
    returns a list of comma seperated value lines
    """
    stock = 'AAPL'
    
    day_begin_unix = convert_to_unix(day_begin)
    day_end_unix = convert_to_unix(day_end)
    header, crumb, cookies = get_crumbs_and_cookies(stock)
    
    with requests.session():
        url = 'https://query1.finance.yahoo.com/v7/finance/download/' \
              '{stock}?period1={day_begin}&period2={day_end}&interval={interval}&events=history&crumb={crumb}' \
              .format(stock=stock, 
                      day_begin=day_begin_unix, day_end=day_end_unix,
                      interval=interval, crumb=crumb)
                
        website = requests.get(url, headers=header, cookies=cookies)

    data = pd.read_csv(StringIO(website.text), parse_dates=['Date'], index_col=['Date'])
    data['Returns'] = data['Close'].pct_change()
    return data

def fnYFinJSON(stock, field):
    if not stock:
        return "enter a ticker"
    else:
    	urlData = "https://query2.finance.yahoo.com/v7/finance/quote?symbols="+stock
    	webUrl = urlopen(urlData)
    	if (webUrl.getcode() == 200):
    		data = webUrl.read()
    	else:
    	    print ("Received an error from server, cannot retrieve results " + str(webUrl.getcode()))
    	yFinJSON = json.loads(data)
        
    try:
        tickerData = yFinJSON["quoteResponse"]["result"][0]
    except:
        return "N/A"
    if field in tickerData:
        return tickerData[field]
    else:
        return "N/A"

def fnYFinJSONAll(stock):
	urlData = "https://query2.finance.yahoo.com/v7/finance/quote?symbols="+stock
	df = pd.read_json(urlData)
	df = pd.DataFrame(df.iloc[1][0])#need to go down to result layer
	df.set_index('symbol', inplace=True) #renaming row as the ticker to keep track of data
	return df

# Option Chains Data
def grabExpDates(ticker):
    """
    Returns a dataframe of expiration dates available on Yahoo Finance.
    e.g.: https://query2.finance.yahoo.com/v7/finance/options/SPY
    
    """
    url = "https://query2.finance.yahoo.com/v7/finance/options/" + ticker
    data = pd.read_json(url)
    expDatesUnix = data['optionChain']['result'][0]['expirationDates']
    expDatesNormal = pd.to_datetime(expDatesUnix, origin="unix",unit='s')
    df = pd.DataFrame(expDatesUnix,index=expDatesNormal,columns=["Unix Date"])
    return df

def optionChain(ticker='SPY', date='2022-11-18', calls_puts = 'calls'):
    """
    Scrapes option chain from Yahoo Fiance by converting date to unix code:
        https://query2.finance.yahoo.com/v7/finance/options/{ticker}?date={date}
        e.g.: https://query2.finance.yahoo.com/v7/finance/options/TSLA?date=1668729600
    
    Parameters
    ----------
    ticker : str, optional
        DESCRIPTION. The default is 'SPY'.
    date : str, optional
        DESCRIPTION. Maturity date of options. Enter in yyy-mm-dd format. The default is '2022-11-18'.
    calls_puts : str, optional
        DESCRIPTION. Enter 'calls' or 'puts'. The default is 'calls'.
    Returns
    -------
    dfOptions : DataFrame
        Returns calls or puts option chain.
    """
    url = "https://query2.finance.yahoo.com/v7/finance/options/{}?date={}"
    unixTS = pd.Timestamp('{} 00:00:00'.format(date)).timestamp()
    url = url.format(ticker, int(unixTS))
    data = pd.read_json(url)
    optionsData = data['optionChain']['result'][0]['options'][0]
    dfOptions = pd.DataFrame(optionsData[calls_puts])
    dfOptions['Exp'] = pd.to_datetime(dfOptions['expiration'],origin="unix",unit='s')
    return dfOptions