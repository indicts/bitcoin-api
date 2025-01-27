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

testing = False
blockcypher_tokens = [""]
mongo_uri = ""

app = Flask(__name__)
mongo_client = pymongo.MongoClient(mongo_uri)
db = mongo_client.get_database("btcapi")
col = db.get_collection("col")
colorama.init()

def update_transaction_status(invoice_id, status, txid, final_tx=None):
    col.update_one(
        {"invoice_id": invoice_id}, 
        {"$set": {"status": status, "txid": str(txid), "destination_tx": final_tx}}
    )

def get_crypto_price(from_symbol, to_symbol):
    response = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={from_symbol}&tsyms={to_symbol}")
    return float(response.json()[to_symbol])

async def process_transaction(tx, invoices, status):
    txid = tx.get("hash", "")
    outputs = tx.get("outputs", [])
    
    for invoice in invoices:
        payment = invoice.get("payment", {})
        address = payment.get("address", "")
        sats_threshold = payment.get("amounts", {}).get("sats", 0)
        
        for output in outputs:
            value = output.get("value")
            if not value:
                continue
                
            if address == output["addresses"][0] and value >= sats_threshold:
                print(f"{status} tx detected: {Fore.LIGHTGREEN_EX if status == 'confirmed' else Fore.LIGHTBLUE_EX}{txid}{Fore.RESET}")
                update_transaction_status(invoice["invoice_id"], status, txid)
                
                if status == "confirmed":
                    pkey = PrivateKey(invoice["private_key"])
                    tx_sent = pkey.send(outputs=[], leftover=invoice["destination"])
                    update_transaction_status(invoice["invoice_id"], "completed", txid, tx_sent)

async def handle_transactions(event_type):
    while True:
        network = "test3" if testing else "main"
        token = random.choice(blockcypher_tokens)
        url = f"wss://socket.blockcypher.com/v1/btc/{network}?token={token}"
        
        async with websockets.connect(url) as websocket:
            await websocket.send(json.dumps({"event": f"{event_type}-tx"}))
            
            while True:
                message = await websocket.recv()
                tx = json.loads(message)
                invoices = col.find({})
                await process_transaction(tx, invoices, event_type)

def start_transaction_handlers():
    for handler in ["unconfirmed", "confirmed"]:
        threading.Thread(
            target=lambda h=handler: asyncio.run(handle_transactions(h))
        ).start()

@app.route('/create')
def create_invoice():
    usd_amount = float(request.args.get('usd'))
    destination = request.args.get('destination')
    
    btc_amount = get_crypto_price("USD", "BTC") * usd_amount
    sats_amount = int(btc_amount * 100_000_000)
    
    private_key = PrivateKeyTestnet() if testing else PrivateKey()
    
    invoice = {
        "invoice_id": str(uuid.uuid4()),
        "destination": destination,
        "payment": {
            "address": private_key.address,
            "amounts": {
                "btc": btc_amount,
                "sats": sats_amount,
                "usd": float(format(usd_amount, ".2f"))
            }
        },
        "status": "waiting",
        "private_key": private_key.to_wif()
    }
    
    col.insert_one(invoice)
    del invoice["private_key"]
    return jsonify(invoice)

@app.route('/status')
def get_status():
    invoice_id = request.args.get('invoice_id')
    invoice = col.find_one({'invoice_id': invoice_id})
    
    if not invoice:
        return jsonify({'error': 'Invoice ID not found!'}), 404
        
    return jsonify({
        'status': invoice['status'],
        'txid': invoice.get('txid')
    }), 200

start_transaction_handlers()
app.run()
