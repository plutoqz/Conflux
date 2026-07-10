# Post-Quantum Cryptography Migration Guide

## Executive Summary

The arrival of cryptographically relevant quantum computers (CRQCs) will
render many currently deployed public-key cryptosystems insecure. Organizations
must begin planning their migration to post-quantum cryptography (PQC) now,
even if CRQCs are still years away, because:

1. **Harvest-Now-Decrypt-Later attacks** are already possible
2. **Migration timelines** for large organizations can span 5-15 years
3. **NIST standards** are now available (FIPS 203, 204, 205)
4. **Regulatory pressure** is increasing globally

## Inventory Phase

### Step 1: Cryptographic Inventory

Create a comprehensive inventory of all cryptographic assets:

- **Symmetric keys**: AES, 3DES, ChaCha20
- **Asymmetric keys**: RSA, ECDSA, Ed25519
- **Hash functions**: SHA-2, SHA-3
- **Protocols**: TLS, SSH, IPsec, S/MIME
- **Hardware**: HSMs, smart cards, TPMs
- **Certificates**: X.509, code signing

### Step 2: Risk Assessment

Classify each asset by:
- **Data sensitivity**: What is protected?
- **Longevity**: How long must data remain confidential?
- **Interoperability**: What systems interact with this asset?
- **Vendor dependency**: Does migration require vendor support?

### Step 3: Prioritization

Prioritize migration based on:
1. Data with >10-year confidentiality requirements
2. Public-key infrastructure (PKI) components
3. External-facing systems (TLS, VPN)
4. Code signing and software update mechanisms
5. Internal systems

## Migration Strategy

### Hybrid Approach (Recommended)

Deploy hybrid schemes that combine classical and PQC algorithms:

- **TLS 1.3 with PQC**: Use hybrid key exchange (e.g., ECDH + Kyber)
- **X.509 certificates**: Dual signatures (ECDSA + ML-DSA)
- **SSH**: Hybrid key agreement

This approach provides:
- Backward compatibility with existing systems
- Forward security against future quantum attacks
- Fallback if a PQC algorithm is broken

### Pure PQC Approach

Direct replacement of classical algorithms:
- **Key exchange**: Kyber (ML-KEM) instead of ECDH
- **Signatures**: Dilithium (ML-DSA) instead of ECDSA/RSA
- **Hashing**: SHA-3 or SHA-2 (already quantum-safe)

Advantages: Simpler, smaller attack surface
Disadvantages: No backward compatibility, risk if algorithm is broken

## Algorithm Selection

### Recommended Algorithms (2024)

| Use Case | Primary | Alternative |
|----------|---------|-------------|
| Key Encapsulation | ML-KEM-768 (Kyber) | ML-KEM-1024 |
| Digital Signature | ML-DSA-65 (Dilithium) | SLH-DSA-128s |
| Hash Function | SHA-384 | SHA-512 |
| Symmetric Encryption | AES-256-GCM | AES-256-CTR |

### Security Levels (NIST Categories)

| Level | Classical Bits | Description |
|-------|---------------|-------------|
| 1 | 128 | At least as hard as AES-128 exhaustive key search |
| 2 | 128 | Equivalent to SHA-256 collision search |
| 3 | 192 | At least as hard as AES-192 exhaustive key search |
| 4 | 192 | Equivalent to SHA-384 collision search |
| 5 | 256 | At least as hard as AES-256 exhaustive key search |

## Implementation Considerations

### Performance Impact

PQC algorithms generally have larger key sizes and ciphertexts:

| Algorithm | Public Key | Private Key | Signature/Ciphertext |
|-----------|-----------|-------------|---------------------|
| RSA-2048 | 256 B | 256 B | 256 B |
| ECDSA P-256 | 64 B | 32 B | 64 B |
| ML-KEM-768 | 1184 B | 2400 B | 1088 B |
| ML-DSA-65 | 1952 B | 4000 B | 3293 B |
| SLH-DSA-128s | 32 B | 64 B | 7856 B |

### Protocol Overhead

Larger keys impact:
- **TLS handshake**: Additional ~5-10 KB per handshake
- **TCP fragmentation**: May require MSS adjustment
- **Load balancers**: Buffer size may need increase
- **IoT devices**: Memory constraints may limit algorithm choice

## Testing and Validation

### Interoperability Testing

- Test hybrid implementations with multiple vendors
- Verify fallback behavior when PQC component fails
- Measure performance under realistic load

### Security Testing

- Verify resistance to side-channel attacks
- Test timing attack resistance
- Validate randomness sources
- Check for implementation bugs with test vectors

## Regulatory Compliance

### US Government (OMB M-23-02)
- Federal agencies must inventory cryptographic systems
- Migration plans due by 2024
- Target completion by 2035

### EU (EUCI Regulation)
- EU classified information requires approved cryptography
- PQC migration under evaluation by ENISA

### CNSA 2.0 (NSA)
- Commercial National Security Algorithm Suite 2.0
- Timeline for National Security Systems
- Requires PQC for all NSS by 2033

## Timeline and Milestones

| Year | Milestone |
|------|-----------|
| 2024 | NIST PQC standards published |
| 2024-2026 | Inventory and planning |
| 2025-2028 | Vendor PQC support in products |
| 2026-2030 | Pilot deployments |
| 2028-2033 | Production migration (prioritized) |
| 2030-2035 | Complete migration |

> **Key takeaway**: Start now. The migration will take a decade.
> Every year of delay increases exposure to HNDL attacks.
