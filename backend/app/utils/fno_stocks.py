"""
NSE F&O Stocks Master Universe with authentic cash market reference prices,
Upstox instrument keys, sectors, and lot sizes.
"""

from typing import List, Dict, Any

FNO_STOCKS: List[Dict[str, Any]] = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "instrument_key": "NSE_EQ|INE002A01018", "sector": "Energy", "lot_size": 250, "ref_price": 1211.2},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "instrument_key": "NSE_EQ|INE467B01029", "sector": "IT", "lot_size": 175, "ref_price": 2465.0},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "instrument_key": "NSE_EQ|INE040A01034", "sector": "Banking", "lot_size": 550, "ref_price": 728.85},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "instrument_key": "NSE_EQ|INE090A01021", "sector": "Banking", "lot_size": 700, "ref_price": 1397.0},
    {"symbol": "INFY", "name": "Infosys Ltd", "instrument_key": "NSE_EQ|INE009A01021", "sector": "IT", "lot_size": 400, "ref_price": 1161.2},
    {"symbol": "SBIN", "name": "State Bank of India", "instrument_key": "NSE_EQ|INE062A01020", "sector": "Banking", "lot_size": 1500, "ref_price": 962.6},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "instrument_key": "NSE_EQ|INE397D01024", "sector": "Telecom", "lot_size": 950, "ref_price": 1905.0},
    {"symbol": "ITC", "name": "ITC Ltd", "instrument_key": "NSE_EQ|INE154A01025", "sector": "FMCG", "lot_size": 1600, "ref_price": 263.5},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "instrument_key": "NSE_EQ|INE237A01028", "sector": "Banking", "lot_size": 400, "ref_price": 1780.0},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "instrument_key": "NSE_EQ|INE018A01030", "sector": "Infrastructure", "lot_size": 300, "ref_price": 10907.0},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "instrument_key": "NSE_EQ|INE238A01034", "sector": "Banking", "lot_size": 625, "ref_price": 1290.0},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "instrument_key": "NSE_EQ|INE155A01022", "sector": "Auto", "lot_size": 1425, "ref_price": 920.0},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India", "instrument_key": "NSE_EQ|INE585B01010", "sector": "Auto", "lot_size": 50, "ref_price": 11489.0},
    {"symbol": "SUNPHARMA", "name": "Sun Pharma Industries", "instrument_key": "NSE_EQ|INE044A01036", "sector": "Pharma", "lot_size": 700, "ref_price": 1758.8},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "instrument_key": "NSE_EQ|INE280A01028", "sector": "Consumer", "lot_size": 175, "ref_price": 4444.8},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "instrument_key": "NSE_EQ|INE296A01024", "sector": "Finance", "lot_size": 125, "ref_price": 7150.0},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "instrument_key": "NSE_EQ|INE081A01020", "sector": "Metals", "lot_size": 5500, "ref_price": 175.5},
    {"symbol": "NTPC", "name": "NTPC Ltd", "instrument_key": "NSE_EQ|INE733E01010", "sector": "Power", "lot_size": 1500, "ref_price": 315.15},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation", "instrument_key": "NSE_EQ|INE752E01010", "sector": "Power", "lot_size": 1800, "ref_price": 250.45},
    {"symbol": "M&M", "name": "Mahindra & Mahindra", "instrument_key": "NSE_EQ|INE101A01026", "sector": "Auto", "lot_size": 350, "ref_price": 2920.9},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "instrument_key": "NSE_EQ|INE423A01024", "sector": "Metals", "lot_size": 250, "ref_price": 2692.0},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ", "instrument_key": "NSE_EQ|INE742F01042", "sector": "Infrastructure", "lot_size": 400, "ref_price": 1750.8},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "instrument_key": "NSE_EQ|INE021A01026", "sector": "Consumer", "lot_size": 200, "ref_price": 2331.9},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "instrument_key": "NSE_EQ|INE918I01026", "sector": "Finance", "lot_size": 500, "ref_price": 1729.0},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "instrument_key": "NSE_EQ|INE917I01010", "sector": "Auto", "lot_size": 125, "ref_price": 10405.0},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corp", "instrument_key": "NSE_EQ|INE029A01011", "sector": "Energy", "lot_size": 1800, "ref_price": 293.5},
    {"symbol": "BRITANNIA", "name": "Britannia Industries", "instrument_key": "NSE_EQ|INE216A01030", "sector": "FMCG", "lot_size": 200, "ref_price": 4764.0},
    {"symbol": "CIPLA", "name": "Cipla Ltd", "instrument_key": "NSE_EQ|INE059A01026", "sector": "Pharma", "lot_size": 650, "ref_price": 1325.1},
    {"symbol": "COALINDIA", "name": "Coal India Ltd", "instrument_key": "NSE_EQ|INE522F01014", "sector": "Energy", "lot_size": 2100, "ref_price": 417.2},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Labs", "instrument_key": "NSE_EQ|INE089A01023", "sector": "Pharma", "lot_size": 125, "ref_price": 6650.0},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd", "instrument_key": "NSE_EQ|INE066A01021", "sector": "Auto", "lot_size": 175, "ref_price": 7284.5},
    {"symbol": "GRASIM", "name": "Grasim Industries", "instrument_key": "NSE_EQ|INE047A01021", "sector": "Metals", "lot_size": 475, "ref_price": 2920.0},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "instrument_key": "NSE_EQ|INE860A01027", "sector": "IT", "lot_size": 700, "ref_price": 1380.0},
    {"symbol": "HINDALCO", "name": "Hindalco Industries", "instrument_key": "NSE_EQ|INE038A01020", "sector": "Metals", "lot_size": 1400, "ref_price": 908.0},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "instrument_key": "NSE_EQ|INE030A01027", "sector": "FMCG", "lot_size": 300, "ref_price": 1893.8},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Ltd", "instrument_key": "NSE_EQ|INE095A01012", "sector": "Banking", "lot_size": 500, "ref_price": 877.0},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "instrument_key": "NSE_EQ|INE019A01038", "sector": "Metals", "lot_size": 675, "ref_price": 1216.3},
    {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "instrument_key": "NSE_EQ|INE239A01024", "sector": "FMCG", "lot_size": 25, "ref_price": 1265.5},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "instrument_key": "NSE_EQ|INE213A01029", "sector": "Energy", "lot_size": 3850, "ref_price": 222.0},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance Ltd", "instrument_key": "NSE_EQ|INE721A01013", "sector": "Finance", "lot_size": 300, "ref_price": 3250.0},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "instrument_key": "NSE_EQ|INE192A01025", "sector": "FMCG", "lot_size": 900, "ref_price": 978.9},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "instrument_key": "NSE_EQ|INE669C01036", "sector": "IT", "lot_size": 600, "ref_price": 1790.0},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "instrument_key": "NSE_EQ|INE481G01011", "sector": "Infrastructure", "lot_size": 100, "ref_price": 10907.0},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "instrument_key": "NSE_EQ|INE075A01022", "sector": "IT", "lot_size": 1500, "ref_price": 184.4},
    {"symbol": "BEL", "name": "Bharat Electronics Ltd", "instrument_key": "NSE_EQ|INE263A01024", "sector": "Defense", "lot_size": 5700, "ref_price": 376.85},
    {"symbol": "HAL", "name": "Hindustan Aeronautics", "instrument_key": "NSE_EQ|INE066F01020", "sector": "Defense", "lot_size": 300, "ref_price": 4989.0},
    {"symbol": "TRENT", "name": "Trent Ltd", "instrument_key": "NSE_EQ|INE849A01020", "sector": "Consumer", "lot_size": 400, "ref_price": 2958.7},
    {"symbol": "VEDL", "name": "Vedanta Ltd", "instrument_key": "NSE_EQ|INE205A01025", "sector": "Metals", "lot_size": 2000, "ref_price": 246.1},
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "instrument_key": "NSE_EQ|INE758T01015", "sector": "Consumer", "lot_size": 2000, "ref_price": 265.0},
    {"symbol": "DLF", "name": "DLF Ltd", "instrument_key": "NSE_EQ|INE271C01023", "sector": "Real Estate", "lot_size": 825, "ref_price": 675.0},
    {"symbol": "SIEMENS", "name": "Siemens Ltd", "instrument_key": "NSE_EQ|INE003A01024", "sector": "Infrastructure", "lot_size": 125, "ref_price": 3624.0},
    {"symbol": "ABB", "name": "ABB India Ltd", "instrument_key": "NSE_EQ|INE117A01022", "sector": "Infrastructure", "lot_size": 125, "ref_price": 6801.0},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam Inv & Fin", "instrument_key": "NSE_EQ|INE121A01024", "sector": "Finance", "lot_size": 500, "ref_price": 1574.4},
    {"symbol": "HAVELLS", "name": "Havells India Ltd", "instrument_key": "NSE_EQ|INE176B01034", "sector": "Consumer", "lot_size": 500, "ref_price": 1121.0},
    {"symbol": "BANKBARODA", "name": "Bank of Baroda", "instrument_key": "NSE_EQ|INE028A01039", "sector": "Banking", "lot_size": 2925, "ref_price": 230.4},
    {"symbol": "PFC", "name": "Power Finance Corp", "instrument_key": "NSE_EQ|INE134E01011", "sector": "Finance", "lot_size": 1300, "ref_price": 333.25},
    {"symbol": "RECLTD", "name": "REC Ltd", "instrument_key": "NSE_EQ|INE020B01018", "sector": "Finance", "lot_size": 1400, "ref_price": 307.8},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories", "instrument_key": "NSE_EQ|INE361B01024", "sector": "Pharma", "lot_size": 200, "ref_price": 9144.5},
    {"symbol": "GAIL", "name": "GAIL (India) Ltd", "instrument_key": "NSE_EQ|INE129A01019", "sector": "Energy", "lot_size": 4675, "ref_price": 168.1},
    {"symbol": "AMBUJACEM", "name": "Ambuja Cements Ltd", "instrument_key": "NSE_EQ|INE079A01024", "sector": "Infrastructure", "lot_size": 900, "ref_price": 360.0},
]

def get_universe() -> List[Dict[str, Any]]:
    return FNO_STOCKS

def get_stock_by_symbol(symbol: str) -> Dict[str, Any]:
    sym = symbol.upper().strip()
    for stock in FNO_STOCKS:
        if stock["symbol"] == sym:
            return stock
    return {"symbol": sym, "name": sym, "instrument_key": f"NSE_EQ|{sym}", "sector": "Diversified", "lot_size": 100, "ref_price": 1000.0}
