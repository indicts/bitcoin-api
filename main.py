import asyncio
import json
import uuid
import random
import threading
import pymongo
import colorama

import requests
import websockets
from flask import Flask, request, jsonify
from bit import PrivateKey, PrivateKeyTestnet
from colorama import Fore

TESTING = False # change False to True to make it use bitcoin testnet
BLOCKCYPHER_TOKENS = [""]
MONGO_URI = ""

app = Flask(__name__)
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.get_database("btcapi")
col = db.get_collection("col")
colorama.init()

def update_status(invoice_id, status, txid, final_tx=None):
    col.update_one({"invoice_id": invoice_id}, {"$set": {"status": status, "txid": str(txid), "destination_tx": final_tx}})

def convert(fsym, tsym):
    response = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={fsym}&tsyms={tsym}")
    data = response.json()
    return float(data[tsym])

async def confirmed_handler():
    while True:
        url = f"wss://socket.blockcypher.com/v1/btc/main?token={random.choice(BLOCKCYPHER_TOKENS)}" if not TESTING else f"wss://socket.blockcypher.com/v1/btc/test3?token={random.choice(BLOCKCYPHER_TOKENS)}"
        async with websockets.connect(url) as websocket:
            subscribe_message = {"event": "confirmed-tx"}
            await websocket.send(json.dumps(subscribe_message))
            
            while True:
                message = await websocket.recv()
                tx = json.loads(message)
                outputs = tx.get("outputs", [])
                txid = tx.get("hash", "")
                
                invoices = col.find({})
                for invoice in invoices:
                    payment = invoice.get("payment", {})
                    address = payment.get("address", "")
                    amounts = payment.get("amounts", {})
                    sats_threshold = amounts.get("sats", 0)
                    
                    for output in outputs:
                        addresses = output["addresses"]
                        value = output.get("value", 0)
                        if value == None:
                            pass
                        if address == addresses[0] and value >= sats_threshold:
                            print(f"Confirmed tx detected: {Fore.LIGHTGREEN_EX + str(txid) + Fore.RESET}")
                            update_status(invoice["invoice_id"], "confirmed", txid)
                            pkey = PrivateKey(invoice["private_key"])
                            tx_sent = pkey.send(outputs=[], leftover=invoice["destination"])
                            update_status(invoice["invoice_id"], "completed", txid, tx_sent)

async def unconfirmed_handler():
    while True:
        url = f"wss://socket.blockcypher.com/v1/btc/main?token={random.choice(BLOCKCYPHER_TOKENS)}" if not TESTING else f"wss://socket.blockcypher.com/v1/btc/test3?token={random.choice(BLOCKCYPHER_TOKENS)}"
        async with websockets.connect(url) as websocket:
            subscribe_message = {"event": "unconfirmed-tx"}
            await websocket.send(json.dumps(subscribe_message))
            
            while True:
                message = await websocket.recv()
                tx = json.loads(message)
                outputs = tx.get("outputs", [])
                txid = tx.get("hash", "")
                
                invoices = col.find({})
                for invoice in invoices:
                    payment = invoice.get("payment", {})
                    address = payment.get("address", "")
                    amounts = payment.get("amounts", {})
                    sats_threshold = amounts.get("sats", 0)
                    
                    
                    for output in outputs:
                        addresses = output["addresses"]
                        value = output.get("value")
                        if value == None:
                            pass
                        if address == addresses[0] and value >= sats_threshold:
                            print(f"Unconfirmed tx detected: {Fore.LIGHTBLUE_EX + str(txid) + Fore.RESET}")
                            update_status(invoice["invoice_id"], "unconfirmed", txid)

def run_confirmed_handler():
    asyncio.run(unconfirmed_handler())

def run_unconfirmed_handler():
    asyncio.run(confirmed_handler())

confirmed_thread = threading.Thread(target=run_confirmed_handler)
unconfirmed_thread = threading.Thread(target=run_unconfirmed_handler)

confirmed_thread.start()
unconfirmed_thread.start()

@app.route('/create')
def create():
    usd = request.args.get('usd')
    destination = request.args.get('destination')

    btcusd = convert("USD", "BTC")
    btc = btcusd * float(usd)
    sats = btc * 100_000_000

    if TESTING == False:
        private_key = PrivateKey()
    else:
        
        private_key = PrivateKeyTestnet()
    private_key_str = private_key.to_wif()

    res = {
        "invoice_id": str(uuid.uuid4()),
        "destination": destination,
        "payment": {
            "address": private_key.address,
            "amounts": {
                "btc": btc,
                "sats": int(sats),
                "usd": float(format(float(usd), ".2f"))
            }
        },
        "status": "waiting"
    }

    to_insert_copy = res.copy()
    to_insert_copy['private_key'] = private_key_str

    if '_id' in to_insert_copy:
        del to_insert_copy['_id']

    col.insert_one(to_insert_copy)

    return jsonify(res)


@app.route('/status')
def status():
    invoice_id = request.args.get('invoice_id')
    res = col.find_one({'invoice_id': invoice_id})
    if res:
        txid = res.get('txid')
        return jsonify({'status': res['status'], 'txid': txid}), 200
    else:
        return jsonify({'error': 'Invoice ID not found!'}), 404

if __name__ == "__main__":
    app.run()
