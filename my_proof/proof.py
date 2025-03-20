import json
import logging
import os
from typing import Dict, Any, List, Set

import requests

from my_proof.eip712 import EIP712SignatureVerifier
from my_proof.models.proof_response import ProofResponse

score_threshold = 0.6
sight_datadao_check_duplication_url = "https://sightai.io/api/v1/datadao/batch-check-exist"

class Proof:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proof_response = ProofResponse(dlp_id=config['dlp_id'])
        self.pullers = [puller.lower() for puller in config.get('pullers', [])]
        self.provider_url = config.get('provider_url')
        self.verification_contract_address = config.get('verification_contract_address')

        self.eip712_signature_verifier = EIP712SignatureVerifier(self.provider_url, self.verification_contract_address)

    def generate(self) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof generation")

        # Iterate through files and calculate data validity
        total_score = 0
        total_entries = 0

        for input_filename in os.listdir(self.config['input_dir']):
            input_file = os.path.join(self.config['input_dir'], input_filename)
            if os.path.splitext(input_file)[1].lower() == '.json':
                with open(input_file, 'r') as f:
                    input_data = json.load(f)

                    if input_filename == 'input.json':
                        valid_count = 0
                        quality_count = 0
                        bill_ids = []

                        for element in input_data:
                            total_entries += 1

                            # Build the message dict for the contract (our contract expects { payload: string })
                            message = {"payload": json.dumps(element["data"], separators=(',', ':'))}
                            data_element_id = element["id"]
                            logging.info(f"verify signature for {data_element_id}")
                            valid_signatures = self.verify_multiple_signatures(message, element)
                            if valid_signatures:
                                logging.info(
                                    f"Signature check for element id {element.get('id')} passed.")
                                valid_count += 1
                            else:
                                logging.warning(
                                    f"Invalid or insufficient signatures for element id {element.get('id')}")

                            # Check quality of the data by size
                            try:
                                quantity = float(element["data"].get("sz", "0"))
                            except ValueError:
                                logging.warning(f"Invalid quantity in element id {element.get('id')}")
                                quantity = 0
                            if quantity >= 10:
                                quality_count += 1

                            # Build bill_id for duplication check
                            bill_id = element["data"].get("billId")
                            if bill_id:
                                bill_ids.append(bill_id)

                        # Make batch request to check duplication
                        logging.info(f"check_duplications from {sight_datadao_check_duplication_url}")
                        duplicate_percentage = self.check_duplicates(bill_ids) if bill_ids else 100

                        # Summarize up
                        quality_percentage = quality_count / total_entries if total_entries > 0 else 0
                        authenticity_score = valid_count / total_entries if total_entries > 0 else 0
                        uniqueness_score = 1 - (duplicate_percentage / 100)

                        self.proof_response.quality = quality_percentage
                        self.proof_response.ownership = authenticity_score
                        self.proof_response.authenticity = authenticity_score
                        self.proof_response.uniqueness = uniqueness_score
                    continue

        # Calculate overall score and validity
        total_score = 0.5 * self.proof_response.quality + 0.3 * self.proof_response.ownership + 0.2 * self.proof_response.uniqueness
        self.proof_response.score = total_score
        self.proof_response.valid = total_score >= score_threshold

        # Additional (public) properties to include in the proof about the data
        self.proof_response.attributes = {
            'total_score': total_score,
        }

        # Additional metadata about the proof, written onchain
        self.proof_response.metadata = {
            'dlp_id': self.config['dlp_id'],
        }

        return self.proof_response

    def verify_multiple_signatures(self, message: Dict[str, str], element: Dict[str, Any]) -> bool:
        """Verify multiple signatures and check if they meet the threshold."""
        unique_valid_signers: Set[str] = set()
        signature_count = 0
        N = len(self.pullers)  # Number of pullers
        required_valid_signatures = max(1, (N // 3) + 1)  # At least N/3 + 1 valid signatures

        # Check all possible signature fields: "signature_1", "signature_2", ...
        for key, value in element.items():
            if key.startswith("signature_"):
                recovered = self.eip712_signature_verifier.verify_signature(message, value)
                logging.info(f"recovered signer: ${recovered}")
                if recovered or recovered.lower() in self.pullers:
                    unique_valid_signers.add(recovered.lower())

        signature_count = len(unique_valid_signers)
        return signature_count >= required_valid_signatures

    def check_duplicates(self, bill_ids: list) -> float:
        """Check for duplicate entries via external API."""
        try:
            response = requests.post(
                sight_datadao_check_duplication_url,
                json={"ids": bill_ids},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if 'existPercentage' in result:
                return result['existPercentage']
            else:
                logging.warning("Invalid response format from duplication API.")
                return 0
        except requests.RequestException as e:
            logging.error(f"Error while checking duplicates: {e}")
            return 0

def fetch_random_number() -> float:
    """Demonstrate HTTP requests by fetching a random number from random.org."""
    try:
        response = requests.get('https://www.random.org/decimal-fractions/?num=1&dec=2&col=1&format=plain&rnd=new')
        return float(response.text.strip())
    except requests.RequestException as e:
        logging.warning(f"Error fetching random number: {e}. Using local random.")
        return __import__('random').random()
