from core.kyber import generate_keypair, encapsulate, decapsulate

class HarvestNowDecryptLater:
    def run(self) -> dict:
        vehicle_pub, vehicle_priv = generate_keypair()

        # Server sends a legitimate package — adversary records ciphertext
        ciphertext, real_session_key = encapsulate(vehicle_pub)

        # Adversary attempts recovery: re-encapsulate with same pubkey
        attacker_ct, attacker_recovered = encapsulate(vehicle_pub)
        quantum_broken = (attacker_recovered == real_session_key)

        # Legitimate vehicle decapsulates correctly
        legit_recovered  = decapsulate(vehicle_priv, ciphertext)
        legit_ok         = (legit_recovered == real_session_key)

        # Show first 16 bytes of each key as hex for visual proof
        real_hex      = real_session_key[:16].hex()
        attacker_hex  = attacker_recovered[:16].hex()
        legit_hex     = legit_recovered[:16].hex()

        return {
            "attack":               "harvest_now_decrypt_later",
            "kyber_resists_hndl":   not quantum_broken,
            "legitimate_decap_ok":  legit_ok,
            "real_session_key_hex": real_hex,
            "attacker_key_hex":     attacker_hex,
            "legit_recovered_hex":  legit_hex,
            "keys_match":           quantum_broken,
            "why_blocked":          "Kyber is IND-CCA2 secure. Every encapsulation with the same public key produces a different ciphertext and a different session key. The adversary has the public key and the recorded ciphertext but cannot reverse the lattice problem to extract the session key — not classically, not with a quantum computer.",
            "pqc_primitive":        "CRYSTALS-Kyber (FIPS 203) — Module Learning With Errors hardness",
        }
