import json
import logging
import os
from typing import Dict, Any

import requests

from my_proof.eip712 import verify_signature
from my_proof.models.proof_response import ProofResponse

expected_signer = "0x5b341022794C71279fBC454985b5b9F7371e0821"
score_threshold = 0.6

class Proof:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proof_response = ProofResponse(dlp_id=config['dlp_id'])

    def generate(self) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof generation")

        # Iterate through files and calculate data validity
        account_email = None
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
                        for element in input_data:
                            total_entries += 1

                            # Build the message dict for the contract (our contract expects { payload: string })
                            # Check by EIP-712 signature
                            message = {"payload": json.dumps(element["data"], separators=(',', ':'))}
                            recovered = verify_signature(message, element["signature"])
                            if recovered and recovered.lower() == expected_signer.lower():
                                logging.info(
                                    f"Signature check for element id {element.get('id')} passed"
                                )
                                valid_count += 1
                            else:
                                logging.warning(
                                    f"Invalid signature for element id {element.get('id')}: recovered {recovered}")

                            # Check by size
                            try:
                                quantity = float(element["data"].get("sz", "0"))
                            except ValueError:
                                logging.warning(f"Invalid quantity in element id {element.get('id')}")
                                quantity = 0
                            if quantity >= 10:
                                quality_count += 1

                        quality_percentage = quality_count / total_entries if total_entries > 0 else 0
                        authenticity_score = valid_count / total_entries if total_entries > 0 else 0

                        self.proof_response.quality = quality_percentage
                        self.proof_response.ownership = authenticity_score
                        self.proof_response.authenticity = authenticity_score
                    continue

        # Calculate overall score and validity
        self.proof_response.score = 0.6 * self.proof_response.quality + 0.4 * self.proof_response.ownership
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


def fetch_random_number() -> float:
    """Demonstrate HTTP requests by fetching a random number from random.org."""
    try:
        response = requests.get('https://www.random.org/decimal-fractions/?num=1&dec=2&col=1&format=plain&rnd=new')
        return float(response.text.strip())
    except requests.RequestException as e:
        logging.warning(f"Error fetching random number: {e}. Using local random.")
        return __import__('random').random()
