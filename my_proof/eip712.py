from web3 import Web3
import json

provider_url: str = "https://rpc.moksha.vana.org"
w3 = Web3(Web3.HTTPProvider(provider_url))
contract_address = w3.to_checksum_address("0x5c84d4dBD316252DC79dac7534aEE7F91E29eFAE")

def verify_signature(data: dict, signature: str, ):
    """
    Verifies the signature for the given data using the SightFHEDataDAO contract.

    :param data: The data to verify, in dictionary format.
    :param signature: The signature to verify, in hex format.
    :return: The recovered signer address, or None if verification fails.
    """

    # Load the ABI from the compiled contract JSON
    with open("SightFHEDataDAOVerifier.json") as f:
        contract_artifact = json.load(f)
    abi = contract_artifact["abi"]

    # Create a contract instance
    contract = w3.eth.contract(address=contract_address, abi=abi)

    try:
        # Call the verify function of the contract
        recovered_address = contract.functions.verify(data, signature).call()
        return recovered_address
    except Exception as e:
        print(f"Error during verification: {e}")
        return None
