import web3
import urllib.request
import json
from ens import ENS

from flask import Flask, jsonify
from flask_cors import CORS



from eth_account._utils.signing import extract_chain_id, to_standard_v
from eth_account._utils.legacy_transactions import serializable_unsigned_transaction_from_dict

web3Provider = 'ENTER YOUR INFURA API KEY HERE'

# Initializing endpoints to fetch blockchain data
w3 = web3.Web3(web3.HTTPProvider(web3Provider))
ns = ENS.from_web3(w3)

ETHERSCAN_API_KEY = 'ENTER YOUR ETHERSCAN API KEY HERE';
ETHERSCAN_ENDPOINT = 'https://api.etherscan.io/api';


app = Flask(__name__)
CORS(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'

address =  "0x26b08aa24709091deA01830E7c329DAC370B2c5C"



"""Fetching public key from an address in 0x or ENS format
Given address must have made an outgoing transaction on the ethereum
blockchain. 

"""
@app.route('/getkey/<address>')
def getPubKey(address):
    # converting ENS to 0x format if necessary
    if not address.startswith("0x"):
        address = ns.address(address)

    if not address:
        print('address does not exist')
        return(jsonify(error='address does not exist'), 500)

    # fetching 100 transactions for the adress from the etherscan api
    url = f"{ETHERSCAN_ENDPOINT}?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&offset=100&page=-1&sort=desc&apikey={ETHERSCAN_API_KEY}"
    with urllib.request.urlopen(url) as response:
       tx_list = json.loads(response.read())['result']

    # picking the last outoging transaction and getting it's hash
    for tx_candidate in tx_list:
        if tx_candidate['from'].lower() != address.lower():
            continue
        else:
            tx_hash = tx_candidate['hash']
            break

    # The following code is copied from here:
    # https://gist.github.com/CrackerHax/ec6964ea030d4b31d47b7d412036c623?permalink_comment_id=4657511#gistcomment-4657511
    
    #fetching full transaction data from the infura
    tx = w3.eth.get_transaction(tx_hash)
    tx = dict(tx)

    # reconstructing the transaction in the necessary format
    type_0_keys = ['chainId', 'gas', 'gasPrice', 'nonce', 'to', 'value']
    type_1_keys = ["to",
        "nonce",
        "value",
        "gas",
        'gasPrice',
        "chainId",
        "type"]
    type_2_keys = ["to",
        "nonce",
        "value",
        "gas",
        "chainId",
        "maxFeePerGas",
        "maxPriorityFeePerGas",
        "type"]

    s = w3.eth.account._keys.Signature(vrs=(
        to_standard_v(extract_chain_id(tx["v"])[1]),
        w3.to_int(tx["r"]),
        w3.to_int(tx["s"])
    ))

    if tx["type"] == 0:
        keys_to_get = type_0_keys
    elif tx["type"] == 1:
        keys_to_get = type_1_keys
    elif tx["type"] == 2:
        keys_to_get = type_2_keys

    if "chainId" not in tx:
        # !! This is hardcoded for ETH
        tx["chainId"] = 1

    tt = {k:tx[k] for k in keys_to_get}
    tt["data"] = tx["input"]


    # getting the public address
    ut = serializable_unsigned_transaction_from_dict(tt)
    public_key = s.recover_public_key_from_msg_hash(ut.hash())

    # reconstructing the address from pubkey, to check the result
    from_address = public_key.to_checksum_address()

    if from_address==address:
        return(jsonify({'publicKey': str(public_key)}), 200)
    else:
        return(jsonify(error=f'Could not recover the public key for address : {address}'), 500)
       

if __name__ == '__main__':

   app.run()
