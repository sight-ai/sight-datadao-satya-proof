from web3 import Web3
import json
import logging

# provider_url: str = "https://rpc.moksha.vana.org"
# w3 = Web3(Web3.HTTPProvider(provider_url))
# contract_address = w3.to_checksum_address("0x5c84d4dBD316252DC79dac7534aEE7F91E29eFAE")

class EIP712SignatureVerifier:
    def __init__(self, provider_url: str, verification_contract_address: str):
        """
        Initializes the SightFHEVerifier with a Web3 provider and contract address.

        :param provider_url: The RPC URL of the blockchain node.
        :param verification_contract_address: The address of the SightFHEDataDAO verifier contract.
        """
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract_address = self.w3.to_checksum_address(verification_contract_address)
        self.contract = self._load_contract()

    def _load_contract(self):
        """
        Loads the smart contract using its ABI.

        :return: The contract instance.
        """
        try:
            with open("SightFHEDataDAOVerifier.json") as f:
                contract_artifact = json.load(f)
            abi = contract_artifact["abi"]
            return self.w3.eth.contract(address=self.contract_address, abi=abi)
        except FileNotFoundError:
            logging.error("Contract ABI file not found.")
            raise
        except json.JSONDecodeError:
            logging.error("Error decoding contract ABI JSON file.")
            raise

    def verify_signature(self, data: dict, signature: str) -> str:
        """
        Verifies the signature for the given data using the SightFHEDataDAO contract.

        :param data: The data to verify, in dictionary format.
        :param signature: The signature to verify, in hex format.
        :return: The recovered signer address, or None if verification fails.
        """
        try:
            recovered_address = self.contract.functions.verify(data, signature).call()
            return recovered_address
        except Exception as e:
            logging.error(f"Error during verification: {e}")
            return None