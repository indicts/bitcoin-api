# Bitcoin Python API

A simple bitcoin API to detect payments via bitcoin easily. Create bitcoin invoices & check the status of them. No bitcoin nodes or any of that needed. 

## Installation

1. Install the required packages using pip:

   ```bash
   pip install requests websockets flask bit pymongo colorama
   ```
2. Replace the `BLOCKCYPHER_TOKENS` list and `MONGO_URI` with your BlockCypher API tokens and MongoDB connection URI respectively.
3. Choose whether to use the Bitcoin mainnet or testnet by setting the `TESTING` variable accordingly.
4. Run the file:
   ```bash
   py main.py
   ```
# Endpoints
## Create Invoice
- Endpoint: `/create`
- Method: `GET`
- Query Parameters:
  - `usd` (required): The amount in USD for the invoice.
  - `destination` (required): The final destination address for the invoice.

 - Example:
```
GET /create?usd=100&destination=your_destination_address
```
 - Response:
```json
  {
    "invoice_id": "generated_invoice_id",
    "destination": "your_destination_address",
    "payment": {
      "address": "generated_bitcoin_address",
      "amounts": {
        "btc": bitcoin_amount,
        "sats": satoshis_amount,
        "usd": usd_amount
      }
    },
    "status": "waiting"
  }
  ```
## Check Invoice Status
 - Endpoint: `/status`
 - Method: `GET`
 - Query Parameters:
   - `invoice_id`

 - Example:
```
GET /status?invoice_id=generated_invoice_id
```
  - Response:
```json
{
  "status": "unconfirmed", <- can also be confirmed, waiting, or completed
  "txid": "confirmed_transaction_id"
}
```
# Important Considerations
- This API is for educational and experimental purposes. Please do not rely on this.
- Ensure you have a solid understanding of Bitcoin transactions, confirmations, and security before deploying this API.
- This API does not handle error cases and edge scenarios comprehensively. You may need to enhance error handling and implement additional security measures for production use.
- Be cautious when sharing sensitive information such as private keys, API tokens, and access credentials.
  

