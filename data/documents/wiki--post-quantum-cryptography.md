<!-- source: https://en.wikipedia.org/wiki/Post-quantum_cryptography -->
# Post-quantum cryptography

> Source: https://en.wikipedia.org/wiki/Post-quantum_cryptography
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Cryptography secured against quantum computers
Not to be confused with
Quantum cryptography
.
Post-quantum cryptography(PQC), sometimes referred to asquantum-proof,quantum-safe, orquantum-resistant, is the development ofcryptographic algorithms(usuallypublic-keyalgorithms) that are currently thought, but not proven, to be secure against acryptanalytic attackby aquantum computer.[1]Most widely used public-key algorithms rely on the difficulty of one of three mathematical problems: theinteger factorization problem, thediscrete logarithm problem, or theelliptic-curve discrete logarithm problem. All of these problems could be easily solved on a sufficiently powerful quantum computer runningShor's algorithm[2][3]or possibly alternatives.[4][5]

Post-quantum cryptography
(
PQC
), sometimes referred to as
quantum-proof
,
quantum-safe
, or
quantum-resistant
, is the development of
cryptographic algorithms
(usually
public-key
algorithms) that are currently thought, but not proven, to be secure against a
cryptanalytic attack
by a
quantum computer
.
[
1
]
Most widely used public-key algorithms rely on the difficulty of one of three mathematical problems: the
integer factorization problem
, the
discrete logarithm problem
, or the
elliptic-curve discrete logarithm problem
. All of these problems could be easily solved on a sufficiently powerful quantum computer running
Shor's algorithm
[
2
]
[
3
]
or possibly alternatives.
[
4
]
[
5
]
As of 2026, quantum computers lack theprocessing powerto break widely used cryptographic algorithms;[6]however, because of the length of time required for migration to quantum-safe cryptography, cryptographers are already designing new algorithms to prepare forY2Qor "Q-Day", the day when current algorithms will be vulnerable to quantum computing attacks.Mosca's theoremprovides the risk analysis framework that helps organizations identify how quickly they need to start migrating.

As of 2026, quantum computers lack the
processing power
to break widely used cryptographic algorithms;
[
6
]
however, because of the length of time required for migration to quantum-safe cryptography, cryptographers are already designing new algorithms to prepare for
Y2Q
or "Q-Day", the day when current algorithms will be vulnerable to quantum computing attacks.
Mosca's theorem
provides the risk analysis framework that helps organizations identify how quickly they need to start migrating.
Their work has gained attention from academics and industry through the PQCryptoconferenceseries hosted since 2006, several workshops on Quantum Safe Cryptography hosted by theEuropean Telecommunications Standards Institute(ETSI), and theInstitute for Quantum Computing.[7][8][9]The rumoured existence of widespreadharvest now, decrypt laterprograms has also been seen as a motivation for the early introduction of post-quantum algorithms, as data recorded now may still remain sensitive many years into the future.[10][11][12]

Their work has gained attention from academics and industry through the PQCrypto
conference
series hosted since 2006, several workshops on Quantum Safe Cryptography hosted by the
European Telecommunications Standards Institute
(ETSI), and the
Institute for Quantum Computing
.
[
7
]
[
8
]
[
9
]
The rumoured existence of widespread
harvest now, decrypt later
programs has also been seen as a motivation for the early introduction of post-quantum algorithms, as data recorded now may still remain sensitive many years into the future.
[
10
]
[
11
]
[
12
]
In contrast to the threat quantum computing poses to current public-key algorithms, most currentsymmetric cryptographic algorithmsandhash functionsare considered to be relatively secure against attacks by quantum computers.[3][13]While the quantumGrover's algorithmdoes speed up attacks against symmetric ciphers, doubling the key size can effectively counteract these attacks.[14]Thus post-quantum symmetric cryptography does not need to differ significantly from current symmetric cryptography.

In contrast to the threat quantum computing poses to current public-key algorithms, most current
symmetric cryptographic algorithms
and
hash functions
are considered to be relatively secure against attacks by quantum computers.
[
3
]
[
13
]
While the quantum
Grover's algorithm
does speed up attacks against symmetric ciphers, doubling the key size can effectively counteract these attacks.
[
14
]
Thus post-quantum symmetric cryptography does not need to differ significantly from current symmetric cryptography.
In 2024, the U.S.National Institute of Standards and Technology(NIST) released final versions of its first threePost-Quantum Cryptography Standards.[15]

In 2024, the U.S.
National Institute of Standards and Technology
(NIST) released final versions of its first three
Post-Quantum Cryptography Standards
.
[
15
]

## Migration

Migration
[
edit
]
The transition from classical public-key cryptography to post-quantum cryptography (PQC) is considered a long-term, multi-phase process due to the widespread deployment of cryptographic infrastructure across digital systems. Migration planning is influenced by factors such as data longevity requirements, regulatory guidance, interoperability constraints, and the operational complexity of replacing embedded cryptographic components.[16]

The transition from classical public-key cryptography to post-quantum cryptography (PQC) is considered a long-term, multi-phase process due to the widespread deployment of cryptographic infrastructure across digital systems. Migration planning is influenced by factors such as data longevity requirements, regulatory guidance, interoperability constraints, and the operational complexity of replacing embedded cryptographic components.
[
16
]
One commonly cited risk model is Mosca’s theorem, which estimates the urgency of migration by comparing three time horizons: the time required to transition systems (X), the time during which data must remain secure (Y), and the estimated arrival of cryptographically relevant quantum computers (Z). If X + Y > Z, migration is considered urgent.[16]

One commonly cited risk model is Mosca’s theorem, which estimates the urgency of migration by comparing three time horizons: the time required to transition systems (X), the time during which data must remain secure (Y), and the estimated arrival of cryptographically relevant quantum computers (Z). If X + Y > Z, migration is considered urgent.
[
16
]
A major concern motivating early transition is the “harvest now, decrypt later” threat model, in which encrypted data is intercepted and stored with the intention of decrypting it once large-scale quantum computers become available.[17]

A major concern motivating early transition is the “
harvest now, decrypt later
” threat model, in which encrypted data is intercepted and stored with the intention of decrypting it once large-scale quantum computers become available.
[
17
]
Migration strategies frequently emphasize crypto-agility, the capability of systems to rapidly replace cryptographic primitives without major architectural changes. Hybrid cryptographic deployments where classical and post-quantum algorithms are used simultaneously have been tested in protocols such as Transport Layer Security (TLS) to reduce transitional risk.[18]

Migration strategies frequently emphasize crypto-agility, the capability of systems to rapidly replace cryptographic primitives without major architectural changes. Hybrid cryptographic deployments where classical and post-quantum algorithms are used simultaneously have been tested in protocols such as Transport Layer Security (TLS) to reduce transitional risk.
[
18
]
In 2024, the National Institute of Standards and Technology (NIST) finalized its first post-quantum cryptography standards, including module-lattice-based key encapsulation and digital signature schemes, providing a foundation for structured migration in governmental and commercial systems.[19]

In 2024, the National Institute of Standards and Technology (NIST) finalized its first post-quantum cryptography standards, including module-lattice-based key encapsulation and digital signature schemes, providing a foundation for structured migration in governmental and commercial systems.
[
19
]
International organizations and national cybersecurity agencies have published coordinated roadmaps outlining phased adoption timelines, risk assessments, and procurement guidelines to facilitate a systematic transition.[20]

International organizations and national cybersecurity agencies have published coordinated roadmaps outlining phased adoption timelines, risk assessments, and procurement guidelines to facilitate a systematic transition.
[
20
]

## Monitoring Cryptographically Relevant Quantum Computing Progress

Monitoring Cryptographically Relevant Quantum Computing Progress
[
edit
]
Because the transition to post-quantum cryptography is expected to take many years, organizations increasingly monitor advances in quantum computing to assess whether migration timelines remain appropriate. Rather than relying on a single measurement, researchers and cybersecurity agencies evaluate multiple technical indicators that together provide a more meaningful assessment of progress toward cryptographically relevant quantum computers (CRQCs).

Because the transition to post-quantum cryptography is expected to take many years, organizations increasingly monitor advances in quantum computing to assess whether migration timelines remain appropriate. Rather than relying on a single measurement, researchers and cybersecurity agencies evaluate multiple technical indicators that together provide a more meaningful assessment of progress toward cryptographically relevant quantum computers (CRQCs).
Physical qubit counts alone are generally considered an incomplete measure of cryptographic capability because large numbers of noisy physical qubits may not be able to perform the long, fault-tolerant computations required for practical cryptanalysis. Consequently, greater emphasis is often placed on advances in logical qubits, quantum error correction, gate fidelity, circuit depth, and the successful implementation of quantum algorithms such as Shor's algorithm on increasingly complex problems.

Physical qubit counts alone are generally considered an incomplete measure of cryptographic capability because large numbers of noisy physical qubits may not be able to perform the long, fault-tolerant computations required for practical cryptanalysis. Consequently, greater emphasis is often placed on advances in logical qubits, quantum error correction, gate fidelity, circuit depth, and the successful implementation of quantum algorithms such as Shor's algorithm on increasingly complex problems.
Progress is also assessed through publicly demonstrated cryptographic milestones, including successful attacks against progressively larger instances of integer factorization and elliptic-curve cryptography, improvements in fault-tolerant quantum architectures, and the continued development of post-quantum cryptographic standards by organizations such as the National Institute of Standards and Technology (NIST). Together, these technical and institutional indicators help governments, industry, and researchers evaluate the pace of quantum computing development and adjust long-term migration strategies as new evidence becomes available.

Progress is also assessed through publicly demonstrated cryptographic milestones, including successful attacks against progressively larger instances of integer factorization and elliptic-curve cryptography, improvements in fault-tolerant quantum architectures, and the continued development of post-quantum cryptographic standards by organizations such as the National Institute of Standards and Technology (NIST). Together, these technical and institutional indicators help governments, industry, and researchers evaluate the pace of quantum computing development and adjust long-term migration strategies as new evidence becomes available.

## Preparation

Preparation
[
edit
]
Digital infrastructures require robust cybersecurity. Cryptographic systems are vital to protect the confidentiality and authenticity of data. Quantum computing will be a threat to many of the classical cryptographic algorithms, which are used to achieve these protection goals but are only secure againstclassical computers. Data that is currently not quantum-safe, whether it is stored or transmitted, and that must remain confidential for a long time, may be compromised in the future by quantum computers (“harvest now, decrypt later” attacks). In addition, authenticity will also be jeopardised by quantum computers. The threat that quantum computing poses to cybersecurity can be countered by a timely, comprehensive and coordinated transition to post-quantum cryptography (PQC).[21][22]

Digital infrastructures require robust cybersecurity. Cryptographic systems are vital to protect the confidentiality and authenticity of data. Quantum computing will be a threat to many of the classical cryptographic algorithms, which are used to achieve these protection goals but are only secure against
classical computers
. Data that is currently not quantum-safe, whether it is stored or transmitted, and that must remain confidential for a long time, may be compromised in the future by quantum computers (“harvest now, decrypt later” attacks). In addition, authenticity will also be jeopardised by quantum computers. The threat that quantum computing poses to cybersecurity can be countered by a timely, comprehensive and coordinated transition to post-quantum cryptography (PQC).
[
21
]
[
22
]

## Algorithms

Algorithms
[
edit
]
Post-quantum cryptography research is mostly focused on six different approaches:[3][8]

Post-quantum cryptography research is mostly focused on six different approaches:
[
3
]
[
8
]

### Lattice-based cryptography

Lattice-based cryptography
[
edit
]
Main article:
Lattice-based cryptography
This approach includes cryptographic systems such aslearning with errors,ring learning with errors(ring-LWE),[23][24][25]thering learning with errors key exchangeand 
thering learning with errors signature, the olderNTRUorGGHencryption schemes, and thenewer NTRU 
signatureandBLISS signatures.[26]Some of these schemes like NTRU encryption have been studied for many years 
without anyone finding a feasible attack. Others like the ring-LWE algorithms 
have proofs that their security reduces to a worst-case problem.[27]The Post-Quantum Cryptography Study Group sponsored by the European Commission suggested that the Stehle–Steinfeld variant of NTRU be studied for standardization rather than the NTRU algorithm.[28][29]At that time, NTRU was still patented. Studies have 
indicated that NTRU may have more secure properties than other lattice based algorithms.[30]Two lattice-based 
algorithms,ML-KEM(commonly known as Kyber) and ML-DSA (commonly known 
as Dilithium) were among the first post-quantum algorithms standardised by 
NIST.[31]

This approach includes cryptographic systems such as
learning with errors
,
ring learning with errors
(
ring-LWE
),
[
23
]
[
24
]
[
25
]
the
ring learning with errors key exchange
and 
the
ring learning with errors signature
, the older
NTRU
or
GGH
encryption schemes, and the
newer NTRU 
signature
and
BLISS signatures
.
[
26
]
Some of these schemes like NTRU encryption have been studied for many years 
without anyone finding a feasible attack. Others like the ring-LWE algorithms 
have proofs that their security reduces to a worst-case problem.
[
27
]
The Post-Quantum Cryptography Study Group sponsored by the European Commission suggested that the Stehle–Steinfeld variant of NTRU be studied for standardization rather than the NTRU algorithm.
[
28
]
[
29
]
At that time, NTRU was still patented. Studies have 
indicated that NTRU may have more secure properties than other lattice based algorithms.
[
30
]
Two lattice-based 
algorithms,
ML-KEM
(commonly known as Kyber) and ML-DSA (commonly known 
as Dilithium) were among the first post-quantum algorithms standardised by 
NIST.
[
31
]

### Multivariate cryptography

Multivariate cryptography
[
edit
]
Main article:
Multivariate cryptography
This includes cryptographic systems such as theUnbalanced Oil and Vinegarsignature scheme which is based on the difficulty of solving systems of multivariate equations. Various attempts to build secure multivariate equation encryption schemes have been broken, notably the Rainbow signature.[32]

This includes cryptographic systems such as the
Unbalanced Oil and Vinegar
signature scheme which is based on the difficulty of solving systems of multivariate equations. Various attempts to build secure multivariate equation encryption schemes have been broken, notably the Rainbow signature.
[
32
]

### Hash-based cryptography

Hash-based cryptography
[
edit
]
Main article:
Hash-based cryptography
This includes cryptographic systems such asLamport signatures, theMerkle signature scheme, the XMSS,[33]the SPHINCS,[34]the WOTS and theSPHINCS+schemes. Hash based digital signatures were invented in the late 1970s byRalph Merkleand have been studied ever since as an interesting alternative to number-theoretic digital signatures like RSA and DSA. Their primary drawback is that for any hash-based public key, there is a limit on the number of signatures that can be signed using the corresponding set of private keys. This fact reduced interest in these signatures until interest was revived due to the desire for cryptography that was resistant to attack by quantum computers. There appear to be no patents on the Merkle signature scheme[citation needed]and there exist many non-patented hash functions that could be used with these schemes. The stateful hash-based signature scheme XMSS developed by a team of researchers under the direction ofJohannes Buchmannis described in RFC 8391.[35]

This includes cryptographic systems such as
Lamport signatures
, the
Merkle signature scheme
, the XMSS,
[
33
]
the SPHINCS,
[
34
]
the WOTS and the
SPHINCS
+
schemes. Hash based digital signatures were invented in the late 1970s by
Ralph Merkle
and have been studied ever since as an interesting alternative to number-theoretic digital signatures like RSA and DSA. Their primary drawback is that for any hash-based public key, there is a limit on the number of signatures that can be signed using the corresponding set of private keys. This fact reduced interest in these signatures until interest was revived due to the desire for cryptography that was resistant to attack by quantum computers. There appear to be no patents on the Merkle signature scheme
[
citation needed
]
and there exist many non-patented hash functions that could be used with these schemes. The stateful hash-based signature scheme XMSS developed by a team of researchers under the direction of
Johannes Buchmann
is described in RFC 8391.
[
35
]
Note that all the above schemes are one-time or bounded-time signatures.Moni NaorandMoti YunginventedUOWHFhashing in 1989 and designed a signature based on hashing (the Naor-Yung scheme)[36]which can be unlimited-time in use (the first such signature that does not require trapdoor properties).

Note that all the above schemes are one-time or bounded-time signatures.
Moni Naor
and
Moti Yung
invented
UOWHF
hashing in 1989 and designed a signature based on hashing (the Naor-Yung scheme)
[
36
]
which can be unlimited-time in use (the first such signature that does not require trapdoor properties).

### Code-based cryptography

Code-based cryptography
[
edit
]
This includes cryptographic systems which rely onerror-correcting codes, such as theMcElieceandNiederreiterencryption algorithms and the relatedCourtois, Finiasz and Sendrier Signaturescheme. The original McEliece signature using randomGoppa codeshas withstood scrutiny for over 40 years. However, many variants of the McEliece scheme, which seek to introduce more structure into the code used in order to reduce the size of the keys, have been shown to be insecure.[37]The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended the McEliece public key encryption system as a candidate for long term protection against attacks by quantum computers.[28]In 2025, NIST announced plans to standardize the code-based HQC encryption algorithm.[38]

This includes cryptographic systems which rely on
error-correcting codes
, such as the
McEliece
and
Niederreiter
encryption algorithms and the related
Courtois, Finiasz and Sendrier Signature
scheme. The original McEliece signature using random
Goppa codes
has withstood scrutiny for over 40 years. However, many variants of the McEliece scheme, which seek to introduce more structure into the code used in order to reduce the size of the keys, have been shown to be insecure.
[
37
]
The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended the McEliece public key encryption system as a candidate for long term protection against attacks by quantum computers.
[
28
]
In 2025, NIST announced plans to standardize the code-based HQC encryption algorithm.
[
38
]

### Isogeny-based cryptography

Isogeny-based cryptography
[
edit
]
These cryptographic systems rely on the properties ofisogenygraphs ofelliptic curves(and higher-dimensionalabelian varieties) over finite fields, in particularsupersingular isogeny graphs, to create cryptographic systems. Among the more well-known representatives of this field are theDiffie–Hellman-like key exchangeCSIDH, which can serve as a straightforward quantum-resistant replacement for the Diffie–Hellman andelliptic curve Diffie–Hellmankey-exchange methods that are in widespread use today,[39]and the signature schemeSQIsignwhich is based on the categorical equivalence between supersingular elliptic curves and maximal orders in particular types of quaternion algebras.[40]Another widely noticed construction,SIDH/SIKE, was spectacularly broken in 2022.[41]The attack is however specific to the SIDH/SIKE family of schemes and does not generalize to other isogeny-based constructions.[42]

These cryptographic systems rely on the properties of
isogeny
graphs of
elliptic curves
(and higher-dimensional
abelian varieties
) over finite fields, in particular
supersingular isogeny graphs
, to create cryptographic systems. Among the more well-known representatives of this field are the
Diffie–Hellman
-like key exchange
CSIDH
, which can serve as a straightforward quantum-resistant replacement for the Diffie–Hellman and
elliptic curve Diffie–Hellman
key-exchange methods that are in widespread use today,
[
39
]
and the signature scheme
SQIsign
which is based on the categorical equivalence between supersingular elliptic curves and maximal orders in particular types of quaternion algebras.
[
40
]
Another widely noticed construction,
SIDH/SIKE
, was spectacularly broken in 2022.
[
41
]
The attack is however specific to the SIDH/SIKE family of schemes and does not generalize to other isogeny-based constructions.
[
42
]

### Symmetric key quantum resistance

Symmetric key quantum resistance
[
edit
]
Using sufficiently large key sizes, the symmetric key cryptographic systems likeAESandSNOW 3Gare already resistant to attack by a quantum computer.[43]Further, key management systems and protocols that use symmetric key cryptography instead of public key cryptography, likeKerberosand the3GPP Mobile Network Authentication Structure, are also inherently secure against attack by a quantum computer. Given its widespread deployment in the world, some researchers recommend expanded use of Kerberos-like symmetric key management as an efficient way to get post-quantum cryptography today.[44]

Using sufficiently large key sizes, the symmetric key cryptographic systems like
AES
and
SNOW 3G
are already resistant to attack by a quantum computer.
[
43
]
Further, key management systems and protocols that use symmetric key cryptography instead of public key cryptography, like
Kerberos
and the
3GPP Mobile Network Authentication Structure
, are also inherently secure against attack by a quantum computer. Given its widespread deployment in the world, some researchers recommend expanded use of Kerberos-like symmetric key management as an efficient way to get post-quantum cryptography today.
[
44
]

## Security reductions

Security reductions
[
edit
]
In cryptography research, it is desirable to prove the equivalence of a cryptographic algorithm and a known hard mathematical problem. These proofs are often called "security reductions", and are used to demonstrate the difficulty of cracking the encryption algorithm. In other words, the security of a given cryptographic algorithm is reduced to the security of a known hard problem. Researchers are actively looking for security reductions in the prospects for post-quantum cryptography. Current results are given here:

In cryptography research, it is desirable to prove the equivalence of a cryptographic algorithm and a known hard mathematical problem. These proofs are often called "security reductions", and are used to demonstrate the difficulty of cracking the encryption algorithm. In other words, the security of a given cryptographic algorithm is reduced to the security of a known hard problem. Researchers are actively looking for security reductions in the prospects for post-quantum cryptography. Current results are given here:

### Lattice-based cryptography – Ring-LWE Signature

Lattice-based cryptography – Ring-LWE Signature
[
edit
]
Further information:
Ring learning with errors key exchange
In some versions ofRing-LWEthere is a security reduction to theshortest-vector problem (SVP)in a lattice as a lower bound on the security. The SVP is known to beNP-hard.[27]Specific ring-LWE systems that have provable security reductions include a variant of Lyubashevsky's ring-LWE signatures defined in a paper by Güneysu, Lyubashevsky, and Pöppelmann.[24]The GLYPH signature scheme is a variant of theGüneysu, Lyubashevsky, and Pöppelmann (GLP) signaturewhich takes into account research results that have come after the publication of the GLP signature in 2012. Another Ring-LWE signature is Ring-TESLA.[45]There also exists a "derandomized variant" of LWE, called Learning with Rounding (LWR), which yields "improved speedup (by eliminating sampling small errors from a Gaussian-like distribution with deterministic errors) and bandwidth".[46]While LWE uses the addition of a small error to conceal the lower bits, LWR uses rounding for the same purpose.

In some versions of
Ring-LWE
there is a security reduction to the
shortest-vector problem (SVP)
in a lattice as a lower bound on the security. The SVP is known to be
NP-hard
.
[
27
]
Specific ring-LWE systems that have provable security reductions include a variant of Lyubashevsky's ring-LWE signatures defined in a paper by Güneysu, Lyubashevsky, and Pöppelmann.
[
24
]
The GLYPH signature scheme is a variant of the
Güneysu, Lyubashevsky, and Pöppelmann (GLP) signature
which takes into account research results that have come after the publication of the GLP signature in 2012. Another Ring-LWE signature is Ring-TESLA.
[
45
]
There also exists a "derandomized variant" of LWE, called Learning with Rounding (LWR), which yields "improved speedup (by eliminating sampling small errors from a Gaussian-like distribution with deterministic errors) and bandwidth".
[
46
]
While LWE uses the addition of a small error to conceal the lower bits, LWR uses rounding for the same purpose.

### Lattice-based cryptography – NTRU, BLISS

Lattice-based cryptography – NTRU, BLISS
[
edit
]
The security of theNTRUencryption scheme and the BLISS[26]signature is believed to be related to, but not provably reducible to, theclosest vector problem (CVP)in a lattice. The CVP is known to beNP-hard. The Post-Quantum Cryptography Study Group sponsored by the European Commission suggested that the Stehle–Steinfeld variant of NTRU, whichdoeshave a security reduction, be studied for long term use instead of the original NTRU algorithm.[28]

The security of the
NTRU
encryption scheme and the BLISS
[
26
]
signature is believed to be related to, but not provably reducible to, the
closest vector problem (CVP)
in a lattice. The CVP is known to be
NP-hard
. The Post-Quantum Cryptography Study Group sponsored by the European Commission suggested that the Stehle–Steinfeld variant of NTRU, which
does
have a security reduction, be studied for long term use instead of the original NTRU algorithm.
[
28
]

### Multivariate cryptography – Unbalanced oil and vinegar

Multivariate cryptography – Unbalanced oil and vinegar
[
edit
]
Further information:
Multivariate cryptography
Unbalanced Oil and Vinegarsignature schemes are asymmetriccryptographicprimitives based onmultivariate polynomialsover afinite field⁠F{\displaystyle \mathbb {F} }⁠. Bulygin, Petzoldt, and Buchmann have shown a reduction of generic multivariate quadratic UOV systems to the NP-Hardmultivariate quadratic equation solving problem.[47]

Unbalanced Oil and Vinegar
signature schemes are asymmetric
cryptographic
primitives based on
multivariate polynomials
over a
finite field
⁠
F
{\displaystyle \mathbb {F} }
⁠
. Bulygin, Petzoldt, and Buchmann have shown a reduction of generic multivariate quadratic UOV systems to the NP-Hard
multivariate quadratic equation solving problem
.
[
47
]

### Hash-based cryptography – Merkle signature scheme

Hash-based cryptography – Merkle signature scheme
[
edit
]
Further information:
Hash-based cryptography
and
Merkle signature scheme
In 2005, Luis Garcia proved that there was a security reduction ofMerkle Hash Treesignatures to the security of the underlying hash function. Garcia showed in his paper that if computationally one-way hash functions exist then the Merkle Hash Tree signature is provably secure.[48]

In 2005, Luis Garcia proved that there was a security reduction of
Merkle Hash Tree
signatures to the security of the underlying hash function. Garcia showed in his paper that if computationally one-way hash functions exist then the Merkle Hash Tree signature is provably secure.
[
48
]
Therefore, use of a hash function with a provable reduction of security to a known hard problem would have a provable security reduction of theMerkle treesignature to that known hard problem.[49]

Therefore, use of a hash function with a provable reduction of security to a known hard problem would have a provable security reduction of the
Merkle tree
signature to that known hard problem.
[
49
]
The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended use of the Merkle signature scheme for long term security protection against quantum computers.[28]

The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended use of the Merkle signature scheme for long term security protection against quantum computers.
[
28
]

### Code-based cryptography – McEliece

Code-based cryptography – McEliece
[
edit
]
Further information:
McEliece cryptosystem
The McEliece Encryption System has a security reduction to the syndrome decoding problem (SDP). The SDP is known to beNP-hard.[50]The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended the use of this cryptography for long term protection against attack by a quantum computer.[28]

The McEliece Encryption System has a security reduction to the syndrome decoding problem (SDP). The SDP is known to be
NP-hard
.
[
50
]
The Post-Quantum Cryptography Study Group sponsored by the European Commission has recommended the use of this cryptography for long term protection against attack by a quantum computer.
[
28
]

### Code-based cryptography – RLCE

Code-based cryptography – RLCE
[
edit
]
In 2016, Wang proposed a random linear code encryption scheme RLCE[51]which is based on McEliece schemes. A RLCE scheme can be constructed using any linear code such as Reed-Solomon code by inserting random columns in the underlying linear code generator matrix.

In 2016, Wang proposed a random linear code encryption scheme RLCE
[
51
]
which is based on McEliece schemes. A RLCE scheme can be constructed using any linear code such as Reed-Solomon code by inserting random columns in the underlying linear code generator matrix.

### Supersingular elliptic curve isogeny cryptography

Supersingular elliptic curve isogeny cryptography
[
edit
]
Further information:
Supersingular isogeny key exchange
Security is related to the problem of constructing an isogeny between two supersingular curves with the same number of points. The most recent published investigation of the difficulty of this problem, by Delfs and Galbraith, indicates that this problem is as hard as the inventors of the key exchange suggest that it is.[52]There is no security reduction to a known NP-hard problem.

Security is related to the problem of constructing an isogeny between two supersingular curves with the same number of points. The most recent published investigation of the difficulty of this problem, by Delfs and Galbraith, indicates that this problem is as hard as the inventors of the key exchange suggest that it is.
[
52
]
There is no security reduction to a known NP-hard problem.

## Comparison

Comparison
[
edit
]
One common characteristic of many post-quantum cryptography algorithms is that they require larger key sizes than commonly used "pre-quantum" public key algorithms. There are often tradeoffs to be made in key size, computational efficiency and ciphertext or signature size. The table below lists some values for different schemes at a 128-bit post-quantum security level.

One common characteristic of many post-quantum cryptography algorithms is that they require larger key sizes than commonly used "pre-quantum" public key algorithms. There are often tradeoffs to be made in key size, computational efficiency and ciphertext or signature size. The table below lists some values for different schemes at a 128-bit post-quantum security level.

<!-- table omitted -->

Algorithm
Type
Public key
Private key
Signature
ML-DSA
[
53
]
Lattice
1,312
B
2,560
B
2,420
B
NTRUEncrypt
[
54
]
[
55
]
Lattice
699
B
935
B
Streamlined NTRU Prime
[
citation needed
]
Lattice
154
B
SPHINCS
[
34
]
Hash Signature
1,000
B
1,000
B
41,000
B
SPHINCS+
[
56
]
Hash Signature
32
B
64
B
8,000
B
BLISS
-II
Lattice
7,000
B
2,000
B
5,000
B
GLP-Variant GLYPH Signature
[
24
]
[
57
]
Ring-LWE
2,000
B
400
B
1,800
B
NewHope
[
58
]
Ring-LWE
2,000
B
2,000
B
Goppa-based McEliece
[
28
]
Code-based
1,000,000
B
11,500
B
Random Linear Code based encryption
[
59
]
RLCE
115,000
B
3,000
B
Quasi-cyclic MDPC-based McEliece
[
60
]
Code-based
1,232
B
2,464
B
SIDH
[
61
]
Isogeny
564
B
48
B
SIDH (compressed keys)
[
62
]
Isogeny
330
B
48
B
3072-bit Discrete Log
not PQC
384
B
32
B
96
B
256-bit Elliptic Curve
not PQC
32
B
32
B
65
B
A practical consideration on a choice among post-quantum cryptographic algorithms is the effort required to send public keys over the internet. From this point of view, the Ring-LWE, NTRU, and SIDH algorithms provide key sizes conveniently under 1 kB, hash-signature public keys come in under 5 kB, and MDPC-based McEliece takes about 1 kB. On the other hand, Goppa-based McEliece requires a nearly 1 MB key.

A practical consideration on a choice among post-quantum cryptographic algorithms is the effort required to send public keys over the internet. From this point of view, the Ring-LWE, NTRU, and SIDH algorithms provide key sizes conveniently under 1 kB, hash-signature public keys come in under 5 kB, and MDPC-based McEliece takes about 1 kB. On the other hand, Goppa-based McEliece requires a nearly 1 MB key.

### Lattice-based cryptography – LWE key exchange and Ring-LWE key exchange

Lattice-based cryptography – LWE key exchange and Ring-LWE key exchange
[
edit
]
Further information:
Ring learning with errors key exchange
The fundamental idea of using LWE and Ring LWE for key exchange was proposed and filed at the University of Cincinnati in 2011 by Jintai Ding. The basic idea comes from the associativity of matrix multiplications, and the errors are used to provide the security. The paper[63]appeared in 2012 after a provisional patent application was filed in 2012.

The fundamental idea of using LWE and Ring LWE for key exchange was proposed and filed at the University of Cincinnati in 2011 by Jintai Ding. The basic idea comes from the associativity of matrix multiplications, and the errors are used to provide the security. The paper
[
63
]
appeared in 2012 after a provisional patent application was filed in 2012.
In 2014, Peikert[64]presented a key transport scheme following the same basic idea of Ding's, where the new idea of sending an additional 1 bit signal for rounding in Ding's construction is also used. For somewhat greater than 128bits of security, Singh presents a set of parameters which have 6956-bit public keys for the Peikert's scheme.[65]The corresponding private key would be roughly 14,000 bits.

In 2014, Peikert
[
64
]
presented a key transport scheme following the same basic idea of Ding's, where the new idea of sending an additional 1 bit signal for rounding in Ding's construction is also used. For somewhat greater than 128
bits of security
, Singh presents a set of parameters which have 6956-bit public keys for the Peikert's scheme.
[
65
]
The corresponding private key would be roughly 14,000 bits.
In 2015, an authenticated key exchange with provable forward security following the same basic idea of Ding's was presented at Eurocrypt 2015,[66]which is an extension of the HMQV[67]construction in Crypto2005. The parameters for different security levels from 80 bits to 350 bits, along with the corresponding key sizes are provided in the paper.[66]

In 2015, an authenticated key exchange with provable forward security following the same basic idea of Ding's was presented at Eurocrypt 2015,
[
66
]
which is an extension of the HMQV
[
67
]
construction in Crypto2005. The parameters for different security levels from 80 bits to 350 bits, along with the corresponding key sizes are provided in the paper.
[
66
]

### Lattice-based cryptography – NTRU encryption

Lattice-based cryptography – NTRU encryption
[
edit
]
Further information:
NTRUEncrypt
For 128 bits of security in NTRU,ntruhps2048509with n = 509 and q = 2048 was selected in the NIST submission in September 2020.[68]This results in a public key of 699 bytes and a corresponding private key of 935 bytes.[55]

For 128 bits of security in NTRU,

```
ntruhps2048509
```

ntruhps2048509
with n = 509 and q = 2048 was selected in the NIST submission in September 2020.
[
68
]
This results in a public key of 699 bytes and a corresponding private key of 935 bytes.
[
55
]

### Multivariate cryptography

Multivariate cryptography
[
edit
]
Further information:
Multivariate cryptography

<!-- table omitted -->

This section
needs expansion
. You can help by
adding missing information
.
(
March 2026
)

### Hash-based cryptography – Merkle signature scheme

Hash-based cryptography – Merkle signature scheme
[
edit
]
Further information:
Hash-based cryptography
and
Merkle signature scheme
In order to get 128 bits of security for hash based signatures to sign 1 million messages using the fractal Merkle tree method of Naor Shenhav and Wool the public and private key sizes are roughly 36,000 bits in length.[69]

In order to get 128 bits of security for hash based signatures to sign 1 million messages using the fractal Merkle tree method of Naor Shenhav and Wool the public and private key sizes are roughly 36,000 bits in length.
[
69
]

### Code-based cryptography – McEliece

Code-based cryptography – McEliece
[
edit
]
Further information:
McEliece cryptosystem
For 128 bits of security in a McEliece scheme, The European Commission's Post-Quantum Cryptography Study group recommends using a binary Goppa code of length at leastn= 6960and dimension at leastk= 5413, and capable of correctingt= 119errors. With these parameters the public key for the McEliece system will be a systematic generator matrix whose non-identity part takesk× (n−k) = 8373911bits. The corresponding private key, which consists of the code support withn= 6960elements from GF(213) and a generator polynomial of witht= 119coefficients from GF(213), will be 92,027 bits in length.[28]

For 128 bits of security in a McEliece scheme, The European Commission's Post-Quantum Cryptography Study group recommends using a binary Goppa code of length at least
n
= 6960
and dimension at least
k
= 5413
, and capable of correcting
t
= 119
errors. With these parameters the public key for the McEliece system will be a systematic generator matrix whose non-identity part takes
k
× (
n
−
k
) = 8373911
bits. The corresponding private key, which consists of the code support with
n
= 6960
elements from GF(2
13
) and a generator polynomial of with
t
= 119
coefficients from GF(2
13
), will be 92,027 bits in length.
[
28
]
The group is also investigating the use of Quasi-cyclic MDPC codes of length at leastn= 216+ 6 = 65542and dimension at leastk= 215+ 3 = 32771, and capable of correctingt= 264errors. With these parameters the public key for the McEliece system will be the first row of a systematic generator matrix whose non-identity part takesk= 32771bits. The private key, a quasi-cyclic parity-check matrix withd= 274nonzero entries on a column (or twice as much on a row), takes no more thand× 16 = 4384bits when represented as the coordinates of the nonzero entries on the first row.

The group is also investigating the use of Quasi-cyclic MDPC codes of length at least
n
= 2
16
+ 6 = 65542
and dimension at least
k
= 2
15
+ 3 = 32771
, and capable of correcting
t
= 264
errors. With these parameters the public key for the McEliece system will be the first row of a systematic generator matrix whose non-identity part takes
k
= 32771
bits. The private key, a quasi-cyclic parity-check matrix with
d
= 274
nonzero entries on a column (or twice as much on a row), takes no more than
d
× 16 = 4384
bits when represented as the coordinates of the nonzero entries on the first row.
Barreto et al. recommend using a binary Goppa code of length at leastn= 3307and dimension at leastk= 2515, and capable of correctingt= 66errors. With these parameters the public key for the McEliece system will be a systematic generator matrix whose non-identity part takesk× (n−k) = 1991880bits.[70]The corresponding private key, which consists of the code support withn= 3307elements from GF(212) and a generator polynomial oft= 66coefficients from GF(212), will be 40,476 bits in length.

Barreto et al. recommend using a binary Goppa code of length at least
n
= 3307
and dimension at least
k
= 2515
, and capable of correcting
t
= 66
errors. With these parameters the public key for the McEliece system will be a systematic generator matrix whose non-identity part takes
k
× (
n
−
k
) = 1991880
bits.
[
70
]
The corresponding private key, which consists of the code support with
n
= 3307
elements from GF(2
12
) and a generator polynomial of
t
= 66
coefficients from GF(2
12
), will be 40,476 bits in length.

### Supersingular elliptic curve isogeny cryptography

Supersingular elliptic curve isogeny cryptography
[
edit
]
Further information:
Supersingular isogeny key exchange
For 128 bits of security in the supersingular isogeny Diffie–Hellman (SIDH) method, De Feo, Jao and Plut recommend using a supersingular curve modulo of a 768-bit prime. If one uses elliptic curve point compression, the public key will need to be no more than 8x768 or 6144 bits in length.[71]A March 2016 paper by authors Azarderakhsh, Jao, Kalach, Koziel, and Leonardi showed how to cut the number of bits transmitted in half, which was further improved by authors Costello, Jao, Longa, Naehrig, Renes and Urbanik resulting in a compressed-key version of the SIDH protocol with public keys only 2640 bits in size.[62]This makes the number of bits transmitted roughly equivalent to the non-quantum secure RSA and Diffie–Hellman at the same classical security level.[72]

For 128 bits of security in the supersingular isogeny Diffie–Hellman (SIDH) method, De Feo, Jao and Plut recommend using a supersingular curve modulo of a 768-bit prime. If one uses elliptic curve point compression, the public key will need to be no more than 8x768 or 6144 bits in length.
[
71
]
A March 2016 paper by authors Azarderakhsh, Jao, Kalach, Koziel, and Leonardi showed how to cut the number of bits transmitted in half, which was further improved by authors Costello, Jao, Longa, Naehrig, Renes and Urbanik resulting in a compressed-key version of the SIDH protocol with public keys only 2640 bits in size.
[
62
]
This makes the number of bits transmitted roughly equivalent to the non-quantum secure RSA and Diffie–Hellman at the same classical security level.
[
72
]

### Symmetric-key–based cryptography

Symmetric-key–based cryptography
[
edit
]
As a general rule, for 128 bits of security in a symmetric-key–based system, one can safely use key sizes of 256 bits. The best quantum attack against arbitrary symmetric-key systems is an application ofGrover's algorithm, which requires work proportional to the square root of the size of the key space. To transmit an encrypted key to a device that possesses the symmetric key necessary to decrypt that key requires roughly 256 bits as well. It is clear that symmetric-key systems offer the smallest key sizes for post-quantum cryptography.[citation needed]

As a general rule, for 128 bits of security in a symmetric-key–based system, one can safely use key sizes of 256 bits. The best quantum attack against arbitrary symmetric-key systems is an application of
Grover's algorithm
, which requires work proportional to the square root of the size of the key space. To transmit an encrypted key to a device that possesses the symmetric key necessary to decrypt that key requires roughly 256 bits as well. It is clear that symmetric-key systems offer the smallest key sizes for post-quantum cryptography.
[
citation needed
]

## Forward secrecy

Forward secrecy
[
edit
]
A public-key system demonstrates a property referred to as perfectforward secrecywhen it generates random public keys per session for the purposes of key agreement. This means that the compromise of one message cannot lead to the compromise of others, and also that there is not a single secret value which can lead to the compromise of multiple messages. Security experts recommend using cryptographic algorithms that support forward secrecy over those that do not.[73]The reason for this is that forward secrecy can protect against the compromise of long term private keys associated with public/private key pairs. This is viewed as a means of preventingmass surveillanceby intelligence agencies.

A public-key system demonstrates a property referred to as perfect
forward secrecy
when it generates random public keys per session for the purposes of key agreement. This means that the compromise of one message cannot lead to the compromise of others, and also that there is not a single secret value which can lead to the compromise of multiple messages. Security experts recommend using cryptographic algorithms that support forward secrecy over those that do not.
[
73
]
The reason for this is that forward secrecy can protect against the compromise of long term private keys associated with public/private key pairs. This is viewed as a means of preventing
mass surveillance
by intelligence agencies.
Both the Ring-LWE key exchange and supersingular isogeny Diffie–Hellman (SIDH) key exchange can support forward secrecy in one exchange with the other party. Both the Ring-LWE and SIDH can also be used without forward secrecy by creating a variant of the classicElGamal encryptionvariant of Diffie–Hellman.

Both the Ring-LWE key exchange and supersingular isogeny Diffie–Hellman (SIDH) key exchange can support forward secrecy in one exchange with the other party. Both the Ring-LWE and SIDH can also be used without forward secrecy by creating a variant of the classic
ElGamal encryption
variant of Diffie–Hellman.
The other algorithms in this article, such as NTRU, do not support forward secrecy as is.

The other algorithms in this article, such as NTRU, do not support forward secrecy as is.
Any authenticated public key encryption system can be used to build a key exchange with forward secrecy.[74]

Any authenticated public key encryption system can be used to build a key exchange with forward secrecy.
[
74
]

## Open Quantum Safe project

Open Quantum Safe project
[
edit
]
TheOpen Quantum Safe(OQS) project was started in late 2016 and has the goal of developing and prototyping quantum-resistant cryptography.[75][76]It aims to integrate current post-quantum schemes in one library:liboqs.[77]liboqs is an open sourceClibrary for quantum-resistant cryptographic algorithms. It initially focuses on key exchange algorithms but by now includes several signature schemes. It provides a common application programming interface (API) suitable for post-quantum key exchange algorithms, and will collect together various implementations. liboqs will also include a test harness and benchmarking routines to compare performance of post-quantum implementations. Furthermore, OQS also provides integration of liboqs intoOpenSSL.[78]

The
Open Quantum Safe
(
OQS
) project was started in late 2016 and has the goal of developing and prototyping quantum-resistant cryptography.
[
75
]
[
76
]
It aims to integrate current post-quantum schemes in one library:
liboqs
.
[
77
]
liboqs is an open source
C
library for quantum-resistant cryptographic algorithms. It initially focuses on key exchange algorithms but by now includes several signature schemes. It provides a common application programming interface (API) suitable for post-quantum key exchange algorithms, and will collect together various implementations. liboqs will also include a test harness and benchmarking routines to compare performance of post-quantum implementations. Furthermore, OQS also provides integration of liboqs into
OpenSSL
.
[
78
]
As of March 2023, the following key exchange algorithms are supported:[75]

As of March 2023, the following key exchange algorithms are supported:
[
75
]
As of August 2024, NIST has published 3 algorithms below as FIPS standards and the 4th is expected near end of the year:[79]

As of August 2024, NIST has published 3 algorithms below as FIPS standards and the 4th is expected near end of the year:
[
79
]

<!-- table omitted -->

Algorithm
Type
BIKE
[
80
]
codes
Classic McEliece
goppa codes
FIPS-203:
CRYSTALS-Kyber
ML-KEM:
[
81
]
Module
Learning With Error
FIPS-204: CRYSTALS-Dilithium
[
82
]
[
83
]
ML-DSA:
[
84
]
Module
Short Integer Solution
FIPS-205:
SPHINCS+
SLH-DSA:
[
85
]
hash based
FIPS-206:
Falcon
FN-DSA:
[
86
]
Short Integer Solution
Frodo
[
87
]
[
88
]
Learning with errors
HQC
[
89
]
[
90
]
codes
NTRU
[
91
]
Lattice-based cryptography
Older supported versions that have been removed because of the progression of theNIST Post-Quantum Cryptography StandardizationProject are:

Older supported versions that have been removed because of the progression of the
NIST Post-Quantum Cryptography Standardization
Project are:

<!-- table omitted -->

Algorithm
Type
BCNS15
[
92
]
Ring learning with errors key exchange
McBits
[
93
]
Error-correcting codes
NewHope
[
94
]
[
58
]
Ring learning with errors key exchange
SIDH
[
95
]
[
96
]
Supersingular isogeny key exchange

## Implementation

Implementation
[
edit
]
A challenge in post-quantum cryptography is the implementation of potentially quantum safe algorithms into existing systems. There are tests done, for example byMicrosoft Researchimplementing PICNIC in aPKIusingHardware security modules.[97]Test implementations forGoogle'sNewHopealgorithm have also been done byHSMvendors. In August 2023, Google released aFIDO2security key implementation of anECC/Dilithium hybrid signature schema which was done in partnership withETH Zürich.[98]

A challenge in post-quantum cryptography is the implementation of potentially quantum safe algorithms into existing systems. There are tests done, for example by
Microsoft Research
implementing PICNIC in a
PKI
using
Hardware security modules
.
[
97
]
Test implementations for
Google's
NewHope
algorithm have also been done by
HSM
vendors. In August 2023, Google released a
FIDO2
security key implementation of an
ECC
/Dilithium hybrid signature schema which was done in partnership with
ETH Zürich
.
[
98
]
TheSignal Protocolhas usedPost-Quantum Extended Diffie–Hellman(PQXDH) since 2023.[99][100]

The
Signal Protocol
has used
Post-Quantum Extended Diffie–Hellman
(PQXDH) since 2023.
[
99
]
[
100
]
On February 21, 2024,Appleannounced that they were going to upgrade theiriMessageprotocol with a new PQC protocol called "PQ3", which will use ongoing keying.[101][102][103]Apple stated that, although capable quantum computers do not yet exist, they wanted to mitigate risks from future quantum computers as well as so-called "Harvest now, decrypt later" attack scenarios. Apple stated that they believe their PQ3 implementation provides protections that "surpass those in all other widely deployed messaging apps", because it uses ongoing keying. Apple intended to replace the existing iMessage protocol within all supported conversations with PQ3 by the end of 2024. Apple also defined a scale to make it easier to compare the security properties of messaging apps, with a scale represented by levels ranging from 0 to 3: 0 for no end-to-end by default, 1 for pre-quantum end-to-end by default, 2 for PQC key establishment only (e.g. PQXDH), and 3 for PQC key establishmentandongoing rekeying (PQ3).[101]

On February 21, 2024,
Apple
announced that they were going to upgrade their
iMessage
protocol with a new PQC protocol called "PQ3", which will use ongoing keying.
[
101
]
[
102
]
[
103
]
Apple stated that, although capable quantum computers do not yet exist, they wanted to mitigate risks from future quantum computers as well as so-called "
Harvest now, decrypt later
" attack scenarios. Apple stated that they believe their PQ3 implementation provides protections that "surpass those in all other widely deployed messaging apps", because it uses ongoing keying. Apple intended to replace the existing iMessage protocol within all supported conversations with PQ3 by the end of 2024. Apple also defined a scale to make it easier to compare the security properties of messaging apps, with a scale represented by levels ranging from 0 to 3: 0 for no end-to-end by default, 1 for pre-quantum end-to-end by default, 2 for PQC key establishment only (e.g. PQXDH), and 3 for PQC key establishment
and
ongoing rekeying (PQ3).
[
101
]
TheInternet Engineering Task Forcehas prepared an Internet-Draft using PQC algorithms inMessaging Layer Security(MLS).[104]MLS will be used inRCStext messaging inGoogle MessagesandMessages (Apple).

The
Internet Engineering Task Force
has prepared an Internet-Draft using PQC algorithms in
Messaging Layer Security
(MLS).
[
104
]
MLS will be used in
RCS
text messaging in
Google Messages
and
Messages (Apple)
.
Other notable implementations include:

Other notable implementations include:
- bouncycastle[105]
bouncycastle
[
105
]
- liboqs[106]
liboqs
[
106
]

## Post-quantum cryptography in blockchain systems

Post-quantum cryptography in blockchain systems
[
edit
]
Blockchain systems commonly rely on public-key cryptography, particularly elliptic-curve digital signature algorithms (ECDSA), to authenticate transactions and control asset ownership. These cryptographic schemes are vulnerable to quantum attacks, as Shor’s algorithm can efficiently solve the discrete logarithm problem on which they are based.[107]

Blockchain systems commonly rely on public-key cryptography, particularly elliptic-curve digital signature algorithms (ECDSA), to authenticate transactions and control asset ownership. These cryptographic schemes are vulnerable to quantum attacks, as Shor’s algorithm can efficiently solve the discrete logarithm problem on which they are based.
[
107
]
In many blockchain protocols, public keys are not revealed until a transaction is executed; however, once exposed, they may become susceptible to quantum attacks if adversaries possess sufficiently advanced quantum capabilities. This has led to recommendations that users migrate assets to quantum-resistant address schemes prior to the emergence of large-scale quantum computers.[107]

In many blockchain protocols, public keys are not revealed until a transaction is executed; however, once exposed, they may become susceptible to quantum attacks if adversaries possess sufficiently advanced quantum capabilities. This has led to recommendations that users migrate assets to quantum-resistant address schemes prior to the emergence of large-scale quantum computers.
[
107
]
The integration of post-quantum cryptographic algorithms into blockchain systems presents several technical challenges. Many post-quantum signature schemes require larger key and signature sizes, which can increase transaction size, storage requirements, and network bandwidth usage. Additionally, higher computational costs for verification may affect scalability and throughput in distributed networks.[108]

The integration of post-quantum cryptographic algorithms into blockchain systems presents several technical challenges. Many post-quantum signature schemes require larger key and signature sizes, which can increase transaction size, storage requirements, and network bandwidth usage. Additionally, higher computational costs for verification may affect scalability and throughput in distributed networks.
[
108
]
Hybrid cryptographic approaches combining classical and post-quantum signatures have been proposed as transitional solutions. These approaches aim to maintain backward compatibility while gradually introducing quantum-resistant security mechanisms. Ongoing research is focused on optimizing post-quantum schemes for decentralized environments while balancing security, efficiency, and scalability requirements.

Hybrid cryptographic approaches combining classical and post-quantum signatures have been proposed as transitional solutions. These approaches aim to maintain backward compatibility while gradually introducing quantum-resistant security mechanisms. Ongoing research is focused on optimizing post-quantum schemes for decentralized environments while balancing security, efficiency, and scalability requirements.

### Physical layer complements

Physical layer complements
[
edit
]
While post-quantum algorithms protect data content from future decryption, they do not prevent the interception and storage of the encrypted ciphertext itself (a threat model known as "Harvest now, decrypt later"). To mitigate this risk, some network architectures incorporate physical layer security (PLS) oroptical chaosalongside PQC.[109]

While post-quantum algorithms protect data content from future decryption, they do not prevent the interception and storage of the encrypted ciphertext itself (a threat model known as "
Harvest now, decrypt later
"). To mitigate this risk, some network architectures incorporate physical layer security (PLS) or
optical chaos
alongside PQC.
[
109
]
By burying the optical signal within the noise floor (negativeOSNR) using spectral phase encoding, these physical countermeasures aim to make the transmission unrecordable. This creates a "defense-in-depth" strategy: physical obfuscation prevents the harvesting of ciphertext entirely, ensuring that no data exists for future quantum decryption, while PQC algorithms provide necessary protection for data stored at the endpoints.[110]

By burying the optical signal within the noise floor (negative
OSNR
) using spectral phase encoding, these physical countermeasures aim to make the transmission unrecordable. This creates a "defense-in-depth" strategy: physical obfuscation prevents the harvesting of ciphertext entirely, ensuring that no data exists for future quantum decryption, while PQC algorithms provide necessary protection for data stored at the endpoints.
[
110
]

### Hybrid encryption

Hybrid encryption
[
edit
]
Screenshot of
Cloudflare
Post-Quantum Key Agreement test page showing
Firefox
135.0 using X25519MLKEM768
Google has maintained the use of "hybrid encryption" in its use of post-quantum cryptography: whenever a relatively new post-quantum scheme is used, it is combined with a more proven, non-PQ scheme. This is to ensure that the data are not compromised even if the relatively new PQ algorithm turns out to be vulnerable to non-quantum attacks before Y2Q. This type of scheme is used in its 2016 and 2019 tests for post-quantum TLS,[111]and in its 2023 FIDO2 key.[98]One of the algorithms used in the 2019 test, SIKE, was broken in 2022, but the non-PQ X25519 layer (already used widely in TLS) still protected the data.[111]Apple's PQ3 and Signal's PQXDH are also hybrid.[101]

Google has maintained the use of "hybrid encryption" in its use of post-quantum cryptography: whenever a relatively new post-quantum scheme is used, it is combined with a more proven, non-PQ scheme. This is to ensure that the data are not compromised even if the relatively new PQ algorithm turns out to be vulnerable to non-quantum attacks before Y2Q. This type of scheme is used in its 2016 and 2019 tests for post-quantum TLS,
[
111
]
and in its 2023 FIDO2 key.
[
98
]
One of the algorithms used in the 2019 test, SIKE, was broken in 2022, but the non-PQ X25519 layer (already used widely in TLS) still protected the data.
[
111
]
Apple's PQ3 and Signal's PQXDH are also hybrid.
[
101
]
The NSA and GCHQ argue against hybrid encryption, claiming that it adds complexity to implementation and transition.Daniel J. Bernstein, who supports hybrid encryption, argues that the claims are bogus.[111]

The NSA and GCHQ argue against hybrid encryption, claiming that it adds complexity to implementation and transition.
Daniel J. Bernstein
, who supports hybrid encryption, argues that the claims are bogus.
[
111
]

## Criticisms

Criticisms
[
edit
]
Post-quantum cryptography's need is predicated on traditional, established cryptographic problems being quickly solved by a quantum computer.  However, quantum computers are still under development, and have yet to demonstrate a large scale test of Shor's algorithm, verifying that a quantum speed-up mechanism is possible, and out-performs a classical computer on such problems.  In 2019, a team using theIBM Qquantum computer could factor the numbers 15 and 21, butnot35.[112]Other attempts have been made to simulate quantum computers for larger numbers, but the simulations had no quantum advantage (i.e a speed-up over a classical computer).[113]

Post-quantum cryptography's need is predicated on traditional, established cryptographic problems being quickly solved by a quantum computer.  However, quantum computers are still under development, and have yet to demonstrate a large scale test of Shor's algorithm, verifying that a quantum speed-up mechanism is possible, and out-performs a classical computer on such problems.  In 2019, a team using the
IBM Q
quantum computer could factor the numbers 15 and 21, but
not
35.
[
112
]
Other attempts have been made to simulate quantum computers for larger numbers, but the simulations had no quantum advantage (i.e a speed-up over a classical computer).
[
113
]
While theinteger factorization,discrete logarithm, andelliptic-curve discrete logarithm problemsare potentially broken by the proposed quantum speed-up mechanism, none of the cryptography based on these mathematically difficult problems have been proven unsafe, nor mathematically broken outside of Shor's algorithm, or its derivatives. These cryptograpic systems are used worldwide, and have been extensively tested for vulnerabilities for several decades.  Additionally, while Shor's algorithm proposes apolynomial time(i.e. fast) solution, via a quantum period-finding mechanism (i.e. finding a repeating period where the quantum computer tests all possible periods in parallel, then collapsing on correct a solution, or solutions)[114], such a speed-up has never been proven to exist at scale.

While the
integer factorization
,
discrete logarithm
, and
elliptic-curve discrete logarithm problems
are potentially broken by the proposed quantum speed-up mechanism, none of the cryptography based on these mathematically difficult problems have been proven unsafe, nor mathematically broken outside of Shor's algorithm, or its derivatives. These cryptograpic systems are used worldwide, and have been extensively tested for vulnerabilities for several decades.  Additionally, while Shor's algorithm proposes a
polynomial time
(i.e. fast) solution, via a quantum period-finding mechanism (i.e. finding a repeating period where the quantum computer tests all possible periods in parallel, then collapsing on correct a solution, or solutions)
[
114
]
, such a speed-up has never been proven to exist at scale.
MathematiciansStephen Wolframand Christopher Wolfram have created simulated models based on Branchial Graphs[115]to mimic quantum mechanics, and by extension can emulate systems utilized by quantum computers.  Their research lead Stephen to publicly express mild doubts about the proposedquantum speed-up mechanism's existence, related to the systematic collapse/unwinding of the entangle quantum states down to a usable, error-corrected solution.  That is,doubtsabout the mechanism responsible for thetheoretical quantum advantageutilized by future quantum computers, at scale, where a large number of fully entangled qubits are capable of running Shor's Algorithm against a modern classical problem (e.g.RSA-2048, utilizinginteger factorization).[116]

Mathematicians
Stephen Wolfram
and Christopher Wolfram have created simulated models based on Branchial Graphs
[
115
]
to mimic quantum mechanics, and by extension can emulate systems utilized by quantum computers.  Their research lead Stephen to publicly express mild doubts about the proposed
quantum speed-up mechanism
's existence, related to the systematic collapse/unwinding of the entangle quantum states down to a usable, error-corrected solution.  That is,
doubts
about the mechanism responsible for the
theoretical quantum advantage
utilized by future quantum computers, at scale, where a large number of fully entangled qubits are capable of running Shor's Algorithm against a modern classical problem (e.g.
RSA-2048
, utilizing
integer factorization
).
[
116
]
In 2013,Edward Snowden's NSA leaks confirmed that the largest supercomputers of the time could not breakcorrectly implementedpublic key crypto systems.  Also, theNSAhad not found a mathematical shortcut, despite being the largest employer of mathematicians in the world.  Security analyst and cryptographer,Bruce Schneier, who had access to the Snowden archive, concluded that the math was never broken.[117]Taken in aggregate, if the above criticisms prove to be true, then the need forpost-quantum cryptographyis put into question, along with the need to switch modern business infrastructure ontoless-provencryptographic schemes.

In 2013,
Edward Snowden
's NSA leaks confirmed that the largest supercomputers of the time could not break
correctly implemented
public key crypto systems.  Also, the
NSA
had not found a mathematical shortcut, despite being the largest employer of mathematicians in the world.  Security analyst and cryptographer,
Bruce Schneier
, who had access to the Snowden archive, concluded that the math was never broken.
[
117
]
Taken in aggregate, if the above criticisms prove to be true, then the need for
post-quantum cryptography
is put into question, along with the need to switch modern business infrastructure onto
less-proven
cryptographic schemes.

## See also

See also
[
edit
]
- NIST Post-Quantum Cryptography Standardization
NIST Post-Quantum Cryptography Standardization
- Quantum cryptography– cryptography based on quantum mechanics
Quantum cryptography
– cryptography based on quantum mechanics
- Crypto-shredding– Deleting encryption keys
Crypto-shredding
– Deleting encryption keys

## References

References
[
edit
]
- ^"Post-Quantum Cryptography: A New Security Paradigm for the Post-Quantum Era".Penta Security Inc. 2025-06-05. Retrieved2025-07-10.
^
"Post-Quantum Cryptography: A New Security Paradigm for the Post-Quantum Era"
.
Penta Security Inc
. 2025-06-05
. Retrieved
2025-07-10
.
- ^Shor, Peter W.(1997). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".SIAM Journal on Computing.26(5):1484–1509.arXiv:quant-ph/9508027.Bibcode:1995quant.ph..8027S.doi:10.1137/S0097539795293172.S2CID2337707.
^
Shor, Peter W.
(1997). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".
SIAM Journal on Computing
.
26
(5):
1484–
1509.
arXiv
:
quant-ph/9508027
.
Bibcode
:
1995quant.ph..8027S
.
doi
:
10.1137/S0097539795293172
.
S2CID
2337707
.
- ^abcBernstein, Daniel J.(2009)."Introduction to post-quantum cryptography"(PDF).Post-Quantum Cryptography.
^
a
b
c
Bernstein, Daniel J.
(2009).
"Introduction to post-quantum cryptography"
(PDF)
.
Post-Quantum Cryptography
.
- ^Kramer, Anna (2023)."'Surprising and super cool'. Quantum algorithm offers faster way to hack internet encryption".Science.381(6664): 1270.doi:10.1126/science.adk9443.PMID37733849.S2CID262084525.
^
Kramer, Anna (2023).
"
'Surprising and super cool'. Quantum algorithm offers faster way to hack internet encryption"
.
Science
.
381
(6664): 1270.
doi
:
10.1126/science.adk9443
.
PMID
37733849
.
S2CID
262084525
.
- ^Regev, Oded (2025-02-28)."An Efficient Quantum Factoring Algorithm".Journal of the ACM.72(1):1–13.arXiv:2308.06572.doi:10.1145/3708471.ISSN0004-5411.
^
Regev, Oded (2025-02-28).
"An Efficient Quantum Factoring Algorithm"
.
Journal of the ACM
.
72
(1):
1–
13.
arXiv
:
2308.06572
.
doi
:
10.1145/3708471
.
ISSN
0004-5411
.
- ^Gershon, Eric (2013-01-14)."New qubit control bodes well for future of quantum computing".phys.org.
^
Gershon, Eric (2013-01-14).
"New qubit control bodes well for future of quantum computing"
.
phys.org
.
- ^Heger, Monica (2009-01-01)."Cryptographers Take On Quantum Computers".IEEE Spectrum.
^
Heger, Monica (2009-01-01).
"Cryptographers Take On Quantum Computers"
.
IEEE Spectrum
.
- ^ab"Q&A With Post-Quantum Computing Cryptography Researcher Jintai Ding".IEEE Spectrum. 2008-11-01.
^
a
b
"Q&A With Post-Quantum Computing Cryptography Researcher Jintai Ding"
.
IEEE Spectrum
. 2008-11-01.
- ^"ETSI Quantum Safe Cryptography Workshop".ETSI Quantum Safe Cryptography Workshop. ETSI. October 2014. Archived fromthe originalon 17 August 2016. Retrieved24 February2015.
^
"ETSI Quantum Safe Cryptography Workshop"
.
ETSI Quantum Safe Cryptography Workshop
. ETSI. October 2014. Archived from
the original
on 17 August 2016
. Retrieved
24 February
2015
.
- ^Gasser, Linus (2023), Mulder, Valentin; Mermoud, Alain; Lenders, Vincent; Tellenbach, Bernhard (eds.), "Post-quantum Cryptography",Trends in Data Protection and Encryption Technologies, Cham: Springer Nature Switzerland, pp.47–52,doi:10.1007/978-3-031-33386-6_10,ISBN978-3-031-33386-6{{citation}}:  CS1 maint: work parameter with ISBN (link)
^
Gasser, Linus (2023), Mulder, Valentin; Mermoud, Alain; Lenders, Vincent; Tellenbach, Bernhard (eds.), "Post-quantum Cryptography",
Trends in Data Protection and Encryption Technologies
, Cham: Springer Nature Switzerland, pp.
47–
52,
doi
:
10.1007/978-3-031-33386-6_10
,
ISBN
978-3-031-33386-6

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
- ^Townsend, Kevin (2022-02-16)."Solving the Quantum Decryption 'Harvest Now, Decrypt Later' Problem".SecurityWeek. Retrieved2023-04-09.
^
Townsend, Kevin (2022-02-16).
"Solving the Quantum Decryption 'Harvest Now, Decrypt Later' Problem"
.
SecurityWeek
. Retrieved
2023-04-09
.
- ^"Quantum-Safe Secure Communications"(PDF).UK National Quantum Technologies Programme. October 2021. Retrieved2023-04-09.
^
"Quantum-Safe Secure Communications"
(PDF)
.
UK National Quantum Technologies Programme
. October 2021
. Retrieved
2023-04-09
.
- ^Daniel J. Bernstein(2009-05-17)."Cost analysis of hash collisions: Will quantum computers make SHARCS obsolete?"(PDF).
^
Daniel J. Bernstein
(2009-05-17).
"Cost analysis of hash collisions: Will quantum computers make SHARCS obsolete?"
(PDF)
.
- ^Daniel J. Bernstein(2010-03-03)."Grover vs. McEliece"(PDF).
^
Daniel J. Bernstein
(2010-03-03).
"Grover vs. McEliece"
(PDF)
.
- ^NIST Releases First 3 Finalized Post-Quantum Encryption Standards, NIST, August 13, 2024
^
NIST Releases First 3 Finalized Post-Quantum Encryption Standards
, NIST, August 13, 2024
- ^abMosca, Michele (2018). "Cybersecurity in an era with quantum computers: Will we be ready?".IEEE Security & Privacy.16(5):38–41.doi:10.1109/MSP.2018.3761723.
^
a
b
Mosca, Michele (2018). "Cybersecurity in an era with quantum computers: Will we be ready?".
IEEE Security & Privacy
.
16
(5):
38–
41.
doi
:
10.1109/MSP.2018.3761723
.
- ^Quantum-Safe Secure Communications(PDF)(Report). UK National Quantum Technologies Programme. October 2021. Retrieved28 February2026.
^
Quantum-Safe Secure Communications
(PDF)
(Report). UK National Quantum Technologies Programme. October 2021
. Retrieved
28 February
2026
.
- ^"Experimenting with Post-Quantum Cryptography".Google Security Blog. 7 July 2016. Retrieved28 February2026.
^
"Experimenting with Post-Quantum Cryptography"
.
Google Security Blog
. 7 July 2016
. Retrieved
28 February
2026
.
- ^"NIST Releases First 3 Finalized Post-Quantum Encryption Standards".National Institute of Standards and Technology. 13 August 2024. Retrieved28 February2026.
^
"NIST Releases First 3 Finalized Post-Quantum Encryption Standards"
.
National Institute of Standards and Technology
. 13 August 2024
. Retrieved
28 February
2026
.
- ^Coordinated Implementation Roadmap for the Transition to Post-Quantum Cryptography(Report). European Commission. 23 June 2025. Retrieved28 February2026.
^
Coordinated Implementation Roadmap for the Transition to Post-Quantum Cryptography
(Report). European Commission. 23 June 2025
. Retrieved
28 February
2026
.
- ^"A Coordinated Implementation Roadmap for the Transition to Post-Quantum Cryptography".European Union. 2025-06-23.
^
"A Coordinated Implementation Roadmap for the Transition to Post-Quantum Cryptography"
.
European Union
. 2025-06-23.
- ^"The PQC Migration Handbook".General Intelligence and Security Service. 2024-12-01.
^
"The PQC Migration Handbook"
.
General Intelligence and Security Service
. 2024-12-01.
- ^Peikert, Chris (2014), Mosca, Michele (ed.),"Lattice Cryptography for the Internet"(PDF),Post-Quantum Cryptography, Lecture Notes in Computer Science, vol. 8772, Cham: Springer International Publishing, pp.197–219,Bibcode:2014LNCS.8772..197P,doi:10.1007/978-3-319-11659-4_12,ISBN978-3-319-11658-7, retrieved2025-07-24{{citation}}:  CS1 maint: work parameter with ISBN (link).
^
Peikert, Chris (2014), Mosca, Michele (ed.),
"Lattice Cryptography for the Internet"
(PDF)
,
Post-Quantum Cryptography
, Lecture Notes in Computer Science, vol. 8772, Cham: Springer International Publishing, pp.
197–
219,
Bibcode
:
2014LNCS.8772..197P
,
doi
:
10.1007/978-3-319-11659-4_12
,
ISBN
978-3-319-11658-7
, retrieved
2025-07-24

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
.
- ^abcGüneysu, Tim; Lyubashevsky, Vadim; Pöppelmann, Thomas (2012), Prouff, Emmanuel; Schaumont, Patrick (eds.),"Practical Lattice-Based Cryptography: A Signature Scheme for Embedded Systems"(PDF),Cryptographic Hardware and Embedded Systems – CHES 2012, vol. 7428, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.530–547,doi:10.1007/978-3-642-33027-8_31,ISBN978-3-642-33026-1, retrieved2025-07-24{{citation}}:  CS1 maint: work parameter with ISBN (link).
^
a
b
c
Güneysu, Tim; Lyubashevsky, Vadim; Pöppelmann, Thomas (2012), Prouff, Emmanuel; Schaumont, Patrick (eds.),
"Practical Lattice-Based Cryptography: A Signature Scheme for Embedded Systems"
(PDF)
,
Cryptographic Hardware and Embedded Systems – CHES 2012
, vol. 7428, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.
530–
547,
doi
:
10.1007/978-3-642-33027-8_31
,
ISBN
978-3-642-33026-1
, retrieved
2025-07-24

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
.
- ^Zhang, Jiang; Zhang, Zhenfeng; Ding, Jintai; Snook, Michael; Dagdelen, Özgür (2015), Oswald, Elisabeth; Fischlin, Marc (eds.),"Authenticated Key Exchange from Ideal Lattices"(PDF),Advances in Cryptology – EUROCRYPT 2015, vol. 9057, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.719–751,doi:10.1007/978-3-662-46803-6_24,ISBN978-3-662-46802-9, retrieved2025-07-24{{citation}}:  CS1 maint: work parameter with ISBN (link).
^
Zhang, Jiang; Zhang, Zhenfeng; Ding, Jintai; Snook, Michael; Dagdelen, Özgür (2015), Oswald, Elisabeth; Fischlin, Marc (eds.),
"Authenticated Key Exchange from Ideal Lattices"
(PDF)
,
Advances in Cryptology – EUROCRYPT 2015
, vol. 9057, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.
719–
751,
doi
:
10.1007/978-3-662-46803-6_24
,
ISBN
978-3-662-46802-9
, retrieved
2025-07-24

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
.
- ^abDucas, Léo; Durmus, Alain; Lepoint, Tancrède; Lyubashevsky, Vadim (2013), Canetti, Ran; Garay, Juan A. (eds.),"Lattice Signatures and Bimodal Gaussians"(PDF),Advances in Cryptology – CRYPTO 2013, vol. 8042, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.40–56,Bibcode:2013LNCS.8042...40D,doi:10.1007/978-3-642-40041-4_3,ISBN978-3-642-40040-7, retrieved2025-07-24{{citation}}:  CS1 maint: work parameter with ISBN (link).
^
a
b
Ducas, Léo; Durmus, Alain; Lepoint, Tancrède; Lyubashevsky, Vadim (2013), Canetti, Ran; Garay, Juan A. (eds.),
"Lattice Signatures and Bimodal Gaussians"
(PDF)
,
Advances in Cryptology – CRYPTO 2013
, vol. 8042, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.
40–
56,
Bibcode
:
2013LNCS.8042...40D
,
doi
:
10.1007/978-3-642-40041-4_3
,
ISBN
978-3-642-40040-7
, retrieved
2025-07-24

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
.
- ^abLyubashevsky, Vadim; Peikert, Chris; Regev, Oded (2010), Gilbert, Henri (ed.),"On Ideal Lattices and Learning with Errors over Rings"(PDF),Advances in Cryptology – EUROCRYPT 2010, vol. 6110, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.1–23,Bibcode:2010LNCS.6110....1L,doi:10.1007/978-3-642-13190-5_1,ISBN978-3-642-13189-9, retrieved2025-07-24{{citation}}:  CS1 maint: work parameter with ISBN (link).
^
a
b
Lyubashevsky, Vadim; Peikert, Chris; Regev, Oded (2010), Gilbert, Henri (ed.),
"On Ideal Lattices and Learning with Errors over Rings"
(PDF)
,
Advances in Cryptology – EUROCRYPT 2010
, vol. 6110, Berlin, Germany; Heidelberg, Germany: Springer Berlin Heidelberg, pp.
1–
23,
Bibcode
:
2010LNCS.6110....1L
,
doi
:
10.1007/978-3-642-13190-5_1
,
ISBN
978-3-642-13189-9
, retrieved
2025-07-24

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
.
- ^abcdefgAugot, Daniel; Batina, Lejla;Bernstein, Daniel J.; Bos, Joppe;Buchmann, Johannes; Castryck, Wouter;Dunkelman, Orr; Güneysu, Tim; Gueron, Shay; Hülsing, Andreas;Lange, Tanja; Mohamed, Mohamed Saied Emam; Rechberger, Christian; Schwabe, Peter; Sendrier, Nicolas; Vercauteren, Frederik;Yang, Bo-Yin(7 September 2015)."Initial recommendations of long-term secure post-quantum systems"(PDF).PQCRYPTO. Retrieved13 September2015.
^
a
b
c
d
e
f
g
Augot, Daniel; Batina, Lejla;
Bernstein, Daniel J.
; Bos, Joppe;
Buchmann, Johannes
; Castryck, Wouter;
Dunkelman, Orr
; Güneysu, Tim; Gueron, Shay; Hülsing, Andreas;
Lange, Tanja
; Mohamed, Mohamed Saied Emam; Rechberger, Christian; Schwabe, Peter; Sendrier, Nicolas; Vercauteren, Frederik;
Yang, Bo-Yin
(7 September 2015).
"Initial recommendations of long-term secure post-quantum systems"
(PDF)
.
PQCRYPTO
. Retrieved
13 September
2015
.
- ^Stehlé, Damien; Steinfeld, Ron (2013-01-01)."Making NTRUEncrypt and NTRUSign as Secure as Standard Worst-Case Problems over Ideal Lattices".Cryptology ePrint Archive.
^
Stehlé, Damien; Steinfeld, Ron (2013-01-01).
"Making NTRUEncrypt and NTRUSign as Secure as Standard Worst-Case Problems over Ideal Lattices"
.
Cryptology ePrint Archive
.
- ^Easttom, Chuck (2019-02-01). "An Analysis of Leading Lattice-Based Asymmetric Cryptographic Primitives".2019 IEEE 9th Annual Computing and Communication Workshop and Conference (CCWC). pp.811–818.doi:10.1109/CCWC.2019.8666459.ISBN978-1-7281-0554-3.S2CID77376310.
^
Easttom, Chuck (2019-02-01). "An Analysis of Leading Lattice-Based Asymmetric Cryptographic Primitives".
2019 IEEE 9th Annual Computing and Communication Workshop and Conference (CCWC)
. pp.
811–
818.
doi
:
10.1109/CCWC.2019.8666459
.
ISBN
978-1-7281-0554-3
.
S2CID
77376310
.
- ^"NIST Releases First 3 Finalized Post-Quantum Encryption Standards".National Institute of Standards and Technology. 13 August 2024.
^
"NIST Releases First 3 Finalized Post-Quantum Encryption Standards"
.
National Institute of Standards and Technology
. 13 August 2024.
- ^Beullens, Ward (2022). "Breaking Rainbow Takes a Weekend on a Laptop".Advances in Cryptology - CRYPTO 2022. pp.464–479.ISBN978-3-031-15979-4.
^
Beullens, Ward (2022). "Breaking Rainbow Takes a Weekend on a Laptop".
Advances in Cryptology - CRYPTO 2022
. pp.
464–
479.
ISBN
978-3-031-15979-4
.
- ^Buchmann, Johannes; Dahmen, Erik; Hülsing, Andreas (2011). "XMSS – A Practical Forward Secure Signature Scheme Based on Minimal Security Assumptions".Post-Quantum Cryptography. PQCrypto 2011. Lecture Notes in Computer Science. Vol. 7071. pp.117–129.CiteSeerX10.1.1.400.6086.doi:10.1007/978-3-642-25405-5_8.ISBN978-3-642-25404-8.ISSN0302-9743.
^
Buchmann, Johannes; Dahmen, Erik; Hülsing, Andreas (2011). "XMSS – A Practical Forward Secure Signature Scheme Based on Minimal Security Assumptions".
Post-Quantum Cryptography. PQCrypto 2011
. Lecture Notes in Computer Science. Vol. 7071. pp.
117–
129.
CiteSeerX
10.1.1.400.6086
.
doi
:
10.1007/978-3-642-25405-5_8
.
ISBN
978-3-642-25404-8
.
ISSN
0302-9743
.
- ^abBernstein, Daniel J.; Hopwood, Daira; Hülsing, Andreas;Lange, Tanja; Niederhagen, Ruben; Papachristodoulou, Louiza; Schneider, Michael; Schwabe, Peter; Wilcox-O'Hearn, Zooko (2015). "SPHINCS: Practical Stateless Hash-Based Signatures". InOswald, Elisabeth; Fischlin, Marc (eds.).Advances in Cryptology – EUROCRYPT 2015. Lecture Notes in Computer Science. Vol. 9056. Springer Berlin Heidelberg. pp.368–397.CiteSeerX10.1.1.690.6403.doi:10.1007/978-3-662-46800-5_15.ISBN9783662467992.
^
a
b
Bernstein, Daniel J.; Hopwood, Daira; Hülsing, Andreas;
Lange, Tanja
; Niederhagen, Ruben; Papachristodoulou, Louiza; Schneider, Michael; Schwabe, Peter; Wilcox-O'Hearn, Zooko (2015). "SPHINCS: Practical Stateless Hash-Based Signatures". In
Oswald, Elisabeth
; Fischlin, Marc (eds.).
Advances in Cryptology – EUROCRYPT 2015
. Lecture Notes in Computer Science. Vol. 9056. Springer Berlin Heidelberg. pp.
368–
397.
CiteSeerX
10.1.1.690.6403
.
doi
:
10.1007/978-3-662-46800-5_15
.
ISBN
9783662467992
.
- ^Huelsing, A.; Butin, D.; Gazdag, S.; Rijneveld, J.; Mohaisen, A. (2018)."RFC 8391 – XMSS: eXtended Merkle Signature Scheme".tools.ietf.org.doi:10.17487/RFC8391.
^
Huelsing, A.; Butin, D.; Gazdag, S.; Rijneveld, J.; Mohaisen, A. (2018).
"RFC 8391 – XMSS: eXtended Merkle Signature Scheme"
.
tools.ietf.org
.
doi
:
10.17487/RFC8391
.
- ^Naor, M.; Yung, M. (1989).Universal one-way hash functions and their cryptographic applications. ACM Press. pp.33–43.doi:10.1145/73007.73011.ISBN978-0-89791-307-2.
^
Naor, M.; Yung, M. (1989).
Universal one-way hash functions and their cryptographic applications
. ACM Press. pp.
33–
43.
doi
:
10.1145/73007.73011
.
ISBN
978-0-89791-307-2
.
- ^Overbeck, Raphael; Sendrier (2009). "Code-based cryptography". In Bernstein, Daniel (ed.).Post-Quantum Cryptography. pp.95–145.doi:10.1007/978-3-540-88702-7_4.ISBN978-3-540-88701-0.
^
Overbeck, Raphael; Sendrier (2009). "Code-based cryptography". In Bernstein, Daniel (ed.).
Post-Quantum Cryptography
. pp.
95–
145.
doi
:
10.1007/978-3-540-88702-7_4
.
ISBN
978-3-540-88701-0
.
- ^"NIST Selects HQC as Fifth Algorithm for Post-Quantum Encryption".National Institute of Standards and Technology. 11 March 2025.
^
"NIST Selects HQC as Fifth Algorithm for Post-Quantum Encryption"
.
National Institute of Standards and Technology
. 11 March 2025.
- ^Castryck, Wouter; Lange, Tanja; Martindale, Chloe; Panny, Lorenz; Renes, Joost (2018)."CSIDH: An Efficient Post-Quantum Commutative Group Action". In Peyrin, Thomas; Galbraith, Steven (eds.).Advances in Cryptology – ASIACRYPT 2018. Lecture Notes in Computer Science. Vol. 11274. Cham: Springer International Publishing. pp.395–427.doi:10.1007/978-3-030-03332-3_15.hdl:1854/LU-8619033.ISBN978-3-030-03332-3.S2CID44165584.
^
Castryck, Wouter; Lange, Tanja; Martindale, Chloe; Panny, Lorenz; Renes, Joost (2018).
"CSIDH: An Efficient Post-Quantum Commutative Group Action"
. In Peyrin, Thomas; Galbraith, Steven (eds.).
Advances in Cryptology – ASIACRYPT 2018
. Lecture Notes in Computer Science. Vol. 11274. Cham: Springer International Publishing. pp.
395–
427.
doi
:
10.1007/978-3-030-03332-3_15
.
hdl
:
1854/LU-8619033
.
ISBN
978-3-030-03332-3
.
S2CID
44165584
.
- ^De Feo, Luca; Kohel, David; Leroux, Antonin; Petit, Christophe; Wesolowski, Benjamin (2020)."SQISign: Compact Post-quantum Signatures from Quaternions and Isogenies". In Moriai, Shiho; Wang, Huaxiong (eds.).Advances in Cryptology – ASIACRYPT 2020. Lecture Notes in Computer Science. Vol. 12491. Cham: Springer International Publishing. pp.64–93.doi:10.1007/978-3-030-64837-4_3.hdl:2013/ULB-DIPOT:oai:dipot.ulb.ac.be:2013/318983.ISBN978-3-030-64837-4.ISSN0302-9743.S2CID222265162.
^
De Feo, Luca; Kohel, David; Leroux, Antonin; Petit, Christophe; Wesolowski, Benjamin (2020).
"SQISign: Compact Post-quantum Signatures from Quaternions and Isogenies"
. In Moriai, Shiho; Wang, Huaxiong (eds.).
Advances in Cryptology – ASIACRYPT 2020
. Lecture Notes in Computer Science. Vol. 12491. Cham: Springer International Publishing. pp.
64–
93.
doi
:
10.1007/978-3-030-64837-4_3
.
hdl
:
2013/ULB-DIPOT:oai:dipot.ulb.ac.be:2013/318983
.
ISBN
978-3-030-64837-4
.
ISSN
0302-9743
.
S2CID
222265162
.
- ^Castryck, Wouter; Decru, Thomas (2023), Hazay, Carmit; Stam, Martijn (eds.),"An Efficient Key Recovery Attack on SIDH",Advances in Cryptology – EUROCRYPT 2023, vol. 14008, Cham: Springer Nature Switzerland, pp.423–447,doi:10.1007/978-3-031-30589-4_15,ISBN978-3-031-30588-7,S2CID258240788, retrieved2023-06-21{{citation}}:  CS1 maint: work parameter with ISBN (link)
^
Castryck, Wouter; Decru, Thomas (2023), Hazay, Carmit; Stam, Martijn (eds.),
"An Efficient Key Recovery Attack on SIDH"
,
Advances in Cryptology – EUROCRYPT 2023
, vol. 14008, Cham: Springer Nature Switzerland, pp.
423–
447,
doi
:
10.1007/978-3-031-30589-4_15
,
ISBN
978-3-031-30588-7
,
S2CID
258240788
, retrieved
2023-06-21

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
- ^"Is SIKE broken yet?". Retrieved2023-06-23.
^
"Is SIKE broken yet?"
. Retrieved
2023-06-23
.
- ^Perlner, Ray A.; Cooper, David A. (2009-04-14).Quantum resistant public key cryptography: a survey. ACM. pp.85–93.doi:10.1145/1527017.1527028.ISBN978-1-60558-474-4.
^
Perlner, Ray A.; Cooper, David A. (2009-04-14).
Quantum resistant public key cryptography: a survey
. ACM. pp.
85–
93.
doi
:
10.1145/1527017.1527028
.
ISBN
978-1-60558-474-4
.
- ^Campagna, Matt; Hardjono, Thomas; Pintsov, Leon; Romansky, Brian; Yu, Taylor (2013)."Kerberos Revisited Quantum-Safe Authentication"(PDF). ETSI.
^
Campagna, Matt; Hardjono, Thomas; Pintsov, Leon; Romansky, Brian; Yu, Taylor (2013).
"Kerberos Revisited Quantum-Safe Authentication"
(PDF)
. ETSI.
- ^Akleylek, Sedat; Bindel, Nina; Buchmann, Johannes; Krämer, Juliane; Marson, Giorgia Azzurra (2016), Pointcheval, David; Nitaj, Abderrahmane; Rachidi, Tajjeeddine (eds.),"An Efficient Lattice-Based Signature Scheme with Provably Secure Instantiation",Progress in Cryptology – AFRICACRYPT 2016, vol. 9646, Cham: Springer International Publishing, pp.44–60,doi:10.1007/978-3-319-31517-1_3,ISBN978-3-319-31516-4, retrieved2025-07-27{{citation}}:  CS1 maint: work parameter with ISBN (link)
^
Akleylek, Sedat; Bindel, Nina; Buchmann, Johannes; Krämer, Juliane; Marson, Giorgia Azzurra (2016), Pointcheval, David; Nitaj, Abderrahmane; Rachidi, Tajjeeddine (eds.),
"An Efficient Lattice-Based Signature Scheme with Provably Secure Instantiation"
,
Progress in Cryptology – AFRICACRYPT 2016
, vol. 9646, Cham: Springer International Publishing, pp.
44–
60,
doi
:
10.1007/978-3-319-31517-1_3
,
ISBN
978-3-319-31516-4
, retrieved
2025-07-27

```
{{citation}}
```

{{
citation
}}
:  CS1 maint: work parameter with ISBN (
link
)
- ^Nejatollahi, Hamid; Dutt, Nikil; Ray, Sandip; Regazzoni, Francesco; Banerjee, Indranil; Cammarota, Rosario (2019-02-27)."Post-Quantum Lattice-Based Cryptography Implementations: A Survey".ACM Computing Surveys.51(6):1–41.doi:10.1145/3292548.ISSN0360-0300.S2CID59337649.
^
Nejatollahi, Hamid; Dutt, Nikil; Ray, Sandip; Regazzoni, Francesco; Banerjee, Indranil; Cammarota, Rosario (2019-02-27).
"Post-Quantum Lattice-Based Cryptography Implementations: A Survey"
.
ACM Computing Surveys
.
51
(6):
1–
41.
doi
:
10.1145/3292548
.
ISSN
0360-0300
.
S2CID
59337649
.
- ^Bulygin, Stanislav; Petzoldt; Buchmann (2010). "Towards Provable Security of the Unbalanced Oil and Vinegar Signature Scheme under Direct Attacks".Progress in Cryptology – INDOCRYPT 2010. Lecture Notes in Computer Science. Vol. 6498. pp.17–32.CiteSeerX10.1.1.294.3105.doi:10.1007/978-3-642-17401-8_3.ISBN978-3-642-17400-1.
^
Bulygin, Stanislav; Petzoldt; Buchmann (2010). "Towards Provable Security of the Unbalanced Oil and Vinegar Signature Scheme under Direct Attacks".
Progress in Cryptology – INDOCRYPT 2010
. Lecture Notes in Computer Science. Vol. 6498. pp.
17–
32.
CiteSeerX
10.1.1.294.3105
.
doi
:
10.1007/978-3-642-17401-8_3
.
ISBN
978-3-642-17400-1
.
- ^Pereira, Geovandro; Puodzius, Cassius; Barreto, Paulo (2016). "Shorter hash-based signatures".Journal of Systems and Software.116:95–100.doi:10.1016/j.jss.2015.07.007.
^
Pereira, Geovandro; Puodzius, Cassius; Barreto, Paulo (2016). "Shorter hash-based signatures".
Journal of Systems and Software
.
116
:
95–
100.
doi
:
10.1016/j.jss.2015.07.007
.
- ^Garcia, Luis."On the security and the efficiency of the Merkle signature scheme"(PDF).Cryptology ePrint Archive. IACR. Retrieved19 June2013.
^
Garcia, Luis.
"On the security and the efficiency of the Merkle signature scheme"
(PDF)
.
Cryptology ePrint Archive
. IACR
. Retrieved
19 June
2013
.
- ^Blaum, Mario; Farrell; Tilborg (31 May 2002).Information, Coding and Mathematics. Springer.doi:10.1007/978-1-4757-3585-7.ISBN978-1-4757-3585-7.
^
Blaum, Mario; Farrell; Tilborg (31 May 2002).
Information, Coding and Mathematics
. Springer.
doi
:
10.1007/978-1-4757-3585-7
.
ISBN
978-1-4757-3585-7
.
- ^Wang, Yongge (2016). "Quantum resistant random linear code based public key encryption scheme RLCE".2016 IEEE International Symposium on Information Theory (ISIT). pp.2519–2523.arXiv:1512.08454.Bibcode:2015arXiv151208454W.doi:10.1109/ISIT.2016.7541753.ISBN978-1-5090-1806-2.
^
Wang, Yongge (2016). "Quantum resistant random linear code based public key encryption scheme RLCE".
2016 IEEE International Symposium on Information Theory (ISIT)
. pp.
2519–
2523.
arXiv
:
1512.08454
.
Bibcode
:
2015arXiv151208454W
.
doi
:
10.1109/ISIT.2016.7541753
.
ISBN
978-1-5090-1806-2
.
- ^Delfs, Christina; Galbraith, Steven D. (February 2016)."Computing isogenies between supersingular elliptic curves over F_p".Designs, Codes and Cryptography.78(2):425–440.arXiv:1310.7789.doi:10.1007/s10623-014-0010-1.ISSN0925-1022.
^
Delfs, Christina; Galbraith, Steven D. (February 2016).
"Computing isogenies between supersingular elliptic curves over F_p"
.
Designs, Codes and Cryptography
.
78
(2):
425–
440.
arXiv
:
1310.7789
.
doi
:
10.1007/s10623-014-0010-1
.
ISSN
0925-1022
.
- ^National Institute of Standards and Technology (2024-08-13).Module-Lattice-Based Digital Signature Standard(PDF)(Report). Gaithersburg, MD: National Institute of Standards and Technology.doi:10.6028/nist.fips.204.
^
National Institute of Standards and Technology (2024-08-13).
Module-Lattice-Based Digital Signature Standard
(PDF)
(Report). Gaithersburg, MD: National Institute of Standards and Technology.
doi
:
10.6028/nist.fips.204
.
- ^Hirschborrn, P;Hoffstein; Howgrave-Graham; Whyte."Choosing NTRUEncrypt Parameters in Light of Combined Lattice Reduction and MITM Approaches"(PDF). NTRU. Archived fromthe original(PDF)on 30 January 2013. Retrieved12 May2014.
^
Hirschborrn, P;
Hoffstein
; Howgrave-Graham; Whyte.
"Choosing NTRUEncrypt Parameters in Light of Combined Lattice Reduction and MITM Approaches"
(PDF)
. NTRU. Archived from
the original
(PDF)
on 30 January 2013
. Retrieved
12 May
2014
.
- ^abMeasurements of key-encapsulation mechanisms, 2026, retrieved2026-04-07
^
a
b
Measurements of key-encapsulation mechanisms
, 2026
, retrieved
2026-04-07
- ^Bernstein, Daniel J.; Dobraunig, Christoph; Eichlseder, Maria; Fluhrer, Scott; Gazdag, Stefan-Lukas; Hülsing, Andreas; Kampanakis, Panos; Kölbl, Stefan;Lange, Tanja; Lauridsen, Martin M.; Mendel, Florian; Niederhagen, Ruben; Rechberger, Christian; Rijneveld, Joost; Schwabe, Peter (November 30, 2017)."SPHINCS+: Submission to the NIST post-quantum project"(PDF).
^
Bernstein, Daniel J.
; Dobraunig, Christoph; Eichlseder, Maria; Fluhrer, Scott; Gazdag, Stefan-Lukas; Hülsing, Andreas; Kampanakis, Panos; Kölbl, Stefan;
Lange, Tanja
; Lauridsen, Martin M.; Mendel, Florian; Niederhagen, Ruben; Rechberger, Christian; Rijneveld, Joost; Schwabe, Peter (November 30, 2017).
"SPHINCS+: Submission to the NIST post-quantum project"
(PDF)
.
- ^Chopra, Arjun (2017)."GLYPH: A New Insantiation of the GLP Digital Signature Scheme".Cryptology ePrint Archive.
^
Chopra, Arjun (2017).
"GLYPH: A New Insantiation of the GLP Digital Signature Scheme"
.
Cryptology ePrint Archive
.
- ^abAlkim, Erdem; Ducas, Léo; Pöppelmann, Thomas; Schwabe, Peter (2015)."Post-quantum key exchange – a new hope"(PDF). Cryptology ePrint Archive, Report 2015/1092. Retrieved1 September2017.
^
a
b
Alkim, Erdem; Ducas, Léo; Pöppelmann, Thomas; Schwabe, Peter (2015).
"Post-quantum key exchange – a new hope"
(PDF). Cryptology ePrint Archive, Report 2015/1092
. Retrieved
1 September
2017
.
- ^Wang, Yongge (2017)."Revised Quantum Resistant Public Key Encryption Scheme RLCE and IND-CCA2 Security for McEliece Schemes".Cryptology ePrint Archive.
^
Wang, Yongge (2017).
"Revised Quantum Resistant Public Key Encryption Scheme RLCE and IND-CCA2 Security for McEliece Schemes"
.
Cryptology ePrint Archive
.
- ^Misoczki, R.; Tillich, J. P.; Sendrier, N.; Barreto, P. S. L. M. (2013). "MDPC-McEliece: New McEliece variants from Moderate Density Parity-Check codes".2013 IEEE International Symposium on Information Theory. pp.2069–2073.CiteSeerX10.1.1.259.9109.doi:10.1109/ISIT.2013.6620590.ISBN978-1-4799-0446-4.S2CID9485532.
^
Misoczki, R.; Tillich, J. P.; Sendrier, N.; Barreto, P. S. L. M. (2013). "MDPC-McEliece: New McEliece variants from Moderate Density Parity-Check codes".
2013 IEEE International Symposium on Information Theory
. pp.
2069–
2073.
CiteSeerX
10.1.1.259.9109
.
doi
:
10.1109/ISIT.2013.6620590
.
ISBN
978-1-4799-0446-4
.
S2CID
9485532
.
- ^Costello, Craig; Longa, Patrick; Naehrig, Michael (2016)."Efficient Algorithms for Supersingular Isogeny Diffie–Hellman"(PDF).Advances in Cryptology – CRYPTO 2016. Lecture Notes in Computer Science. Vol. 9814. pp.572–601.doi:10.1007/978-3-662-53018-4_21.ISBN978-3-662-53017-7.
^
Costello, Craig; Longa, Patrick; Naehrig, Michael (2016).
"Efficient Algorithms for Supersingular Isogeny Diffie–Hellman"
(PDF)
.
Advances in Cryptology – CRYPTO 2016
. Lecture Notes in Computer Science. Vol. 9814. pp.
572–
601.
doi
:
10.1007/978-3-662-53018-4_21
.
ISBN
978-3-662-53017-7
.
- ^abCostello, Craig; Jao; Longa; Naehrig; Renes; Urbanik."Efficient Compression of SIDH public keys". Retrieved8 October2016.
^
a
b
Costello, Craig; Jao; Longa; Naehrig; Renes; Urbanik.
"Efficient Compression of SIDH public keys"
. Retrieved
8 October
2016
.
- ^Ding, Jintai; Xie, Xiang; Lin, Xiaodong (2012-01-01)."A Simple Provably Secure Key Exchange Scheme Based on the Learning with Errors Problem".Cryptology ePrint Archive.
^
Ding, Jintai; Xie, Xiang; Lin, Xiaodong (2012-01-01).
"A Simple Provably Secure Key Exchange Scheme Based on the Learning with Errors Problem"
.
Cryptology ePrint Archive
.
- ^Peikert, Chris (2014-01-01)."Lattice Cryptography for the Internet".Cryptology ePrint Archive. Lecture Notes in Computer Science. Vol. 8772. p. 197.Bibcode:2014LNCS.8772..197P.doi:10.1007/978-3-319-11659-4_12.ISBN978-3-319-11658-7.
^
Peikert, Chris (2014-01-01).
"Lattice Cryptography for the Internet"
.
Cryptology ePrint Archive
. Lecture Notes in Computer Science. Vol. 8772. p. 197.
Bibcode
:
2014LNCS.8772..197P
.
doi
:
10.1007/978-3-319-11659-4_12
.
ISBN
978-3-319-11658-7
.
- ^Singh, Vikram (2015)."A Practical Key Exchange for the Internet using Lattice Cryptography".Cryptology ePrint Archive. Retrieved2015-04-18.
^
Singh, Vikram (2015).
"A Practical Key Exchange for the Internet using Lattice Cryptography"
.
Cryptology ePrint Archive
. Retrieved
2015-04-18
.
- ^abZhang, Jiang; Zhang, Zhenfeng; Ding, Jintai; Snook, Michael; Dagdelen, Özgür (2015-04-26). "Authenticated Key Exchange from Ideal Lattices". In Oswald, Elisabeth; Fischlin, Marc (eds.).Advances in Cryptology – EUROCRYPT 2015. Lecture Notes in Computer Science. Vol. 9057. Springer Berlin Heidelberg. pp.719–751.CiteSeerX10.1.1.649.1864.doi:10.1007/978-3-662-46803-6_24.ISBN978-3-662-46802-9.
^
a
b
Zhang, Jiang; Zhang, Zhenfeng; Ding, Jintai; Snook, Michael; Dagdelen, Özgür (2015-04-26). "Authenticated Key Exchange from Ideal Lattices". In Oswald, Elisabeth; Fischlin, Marc (eds.).
Advances in Cryptology – EUROCRYPT 2015
. Lecture Notes in Computer Science. Vol. 9057. Springer Berlin Heidelberg. pp.
719–
751.
CiteSeerX
10.1.1.649.1864
.
doi
:
10.1007/978-3-662-46803-6_24
.
ISBN
978-3-662-46802-9
.
- ^Krawczyk, Hugo (2005-08-14). "HMQV: A High-Performance Secure Diffie–Hellman Protocol". In Shoup, Victor (ed.).Advances in Cryptology – CRYPTO 2005. Lecture Notes in Computer Science. Vol. 3621. Springer. pp.546–566.doi:10.1007/11535218_33.ISBN978-3-540-28114-6.
^
Krawczyk, Hugo (2005-08-14). "HMQV: A High-Performance Secure Diffie–Hellman Protocol". In Shoup, Victor (ed.).
Advances in Cryptology – CRYPTO 2005
. Lecture Notes in Computer Science. Vol. 3621. Springer. pp.
546–
566.
doi
:
10.1007/11535218_33
.
ISBN
978-3-540-28114-6
.
- ^Cong Chen; Oussama Danba; Jeffrey Hoffstein; Andreas Hülsing; Joost Rijneveld; John M. Schanck; Tsunekazu Saito; Peter Schwabe; William Whyte; Keita Xagawa; Takashi Yamakawa; Zhenfei Zhang (2020)."NTRU Algorithm Specifications And Supporting Documentation"(PDF in .tar.gz).
^
Cong Chen; Oussama Danba; Jeffrey Hoffstein; Andreas Hülsing; Joost Rijneveld; John M. Schanck; Tsunekazu Saito; Peter Schwabe; William Whyte; Keita Xagawa; Takashi Yamakawa; Zhenfei Zhang (2020).
"NTRU Algorithm Specifications And Supporting Documentation"
(PDF in .tar.gz)
.
- ^Naor, Dalit; Shenhav, Amir; Wool, Avishai (November 2006). "One-Time Signatures Revisited: Practical Fast Signatures Using Fractal Merkle Tree Traversal".2006 IEEE 24th Convention of Electrical & Electronics Engineers in Israel. IEEE. pp.255–259.doi:10.1109/EEEI.2006.321066.ISBN978-1-4244-0229-8.
^
Naor, Dalit; Shenhav, Amir; Wool, Avishai (November 2006). "One-Time Signatures Revisited: Practical Fast Signatures Using Fractal Merkle Tree Traversal".
2006 IEEE 24th Convention of Electrical & Electronics Engineers in Israel
. IEEE. pp.
255–
259.
doi
:
10.1109/EEEI.2006.321066
.
ISBN
978-1-4244-0229-8
.
- ^Barreto, Paulo S. L. M.; Biasi, Felipe Piazza; Dahab, Ricardo; López-Hernández, Julio César; Morais, Eduardo M. de; Oliveira, Ana D. Salina de; Pereira, Geovandro C. C. F.; Ricardini, Jefferson E. (2014). Koç, Çetin Kaya (ed.).A Panorama of Post-quantum Cryptography. Springer International Publishing. pp.387–439.doi:10.1007/978-3-319-10683-0_16.ISBN978-3-319-10682-3.
^
Barreto, Paulo S. L. M.; Biasi, Felipe Piazza; Dahab, Ricardo; López-Hernández, Julio César; Morais, Eduardo M. de; Oliveira, Ana D. Salina de; Pereira, Geovandro C. C. F.; Ricardini, Jefferson E. (2014). Koç, Çetin Kaya (ed.).
A Panorama of Post-quantum Cryptography
. Springer International Publishing. pp.
387–
439.
doi
:
10.1007/978-3-319-10683-0_16
.
ISBN
978-3-319-10682-3
.
- ^De Feo, Luca; Jao; Plut (2011)."Towards Quantum-Resistant Cryptosystems From Supersingular Elliptic Curve Isogenies"(PDF).Archived(PDF)from the original on 11 February 2014. Retrieved12 May2014.
^
De Feo, Luca; Jao; Plut (2011).
"Towards Quantum-Resistant Cryptosystems From Supersingular Elliptic Curve Isogenies"
(PDF)
.
Archived
(PDF)
from the original on 11 February 2014
. Retrieved
12 May
2014
.
- ^Azarderakhsh, Reza; Jao, David; Kalach, Kassem; Koziel, Brian; Leonardi, Christopher."Key Compression for Isogeny-Based Cryptosystems".eprint.iacr.org. Retrieved2016-03-02.
^
Azarderakhsh, Reza; Jao, David; Kalach, Kassem; Koziel, Brian; Leonardi, Christopher.
"Key Compression for Isogeny-Based Cryptosystems"
.
eprint.iacr.org
. Retrieved
2016-03-02
.
- ^Ristic, Ivan (2013-06-25)."Deploying Forward Secrecy". SSL Labs. Retrieved14 June2014.
^
Ristic, Ivan (2013-06-25).
"Deploying Forward Secrecy"
. SSL Labs
. Retrieved
14 June
2014
.
- ^"Does NTRU provide Perfect Forward Secrecy?".crypto.stackexchange.com.
^
"Does NTRU provide Perfect Forward Secrecy?"
.
crypto.stackexchange.com
.
- ^ab"Open Quantum Safe".openquantumsafe.org.
^
a
b
"Open Quantum Safe"
.
openquantumsafe.org
.
- ^Stebila, Douglas; Mosca, Michele."Post-Quantum Key Exchange for the Internet and the Open Quantum Safe Project".Cryptology ePrint Archive, Report 2016/1017, 2016. Retrieved9 April2017.
^
Stebila, Douglas; Mosca, Michele.
"Post-Quantum Key Exchange for the Internet and the Open Quantum Safe Project"
.
Cryptology ePrint Archive, Report 2016/1017, 2016
. Retrieved
9 April
2017
.
- ^"liboqs: C library for quantum-resistant cryptographic algorithms". 26 November 2017 – via GitHub.
^
"liboqs: C library for quantum-resistant cryptographic algorithms"
. 26 November 2017 – via GitHub.
- ^"oqsprovider: Open Quantum Safe provider for OpenSSL (3.x)". 12 August 2024 – via GitHub.
^
"oqsprovider: Open Quantum Safe provider for OpenSSL (3.x)"
. 12 August 2024 – via GitHub.
- ^"NIST Releases First 3 Finalized Post-Quantum Encryption Standards".NIST. 13 August 2024.
^
"NIST Releases First 3 Finalized Post-Quantum Encryption Standards"
.
NIST
. 13 August 2024.
- ^"BIKE – Bit Flipping Key Encapsulation".bikesuite.org. Retrieved2023-08-21.
^
"BIKE – Bit Flipping Key Encapsulation"
.
bikesuite.org
. Retrieved
2023-08-21
.
- ^"Module-Lattice-Based Key-Encapsulation Mechanism Standard". 2024.doi:10.6028/NIST.FIPS.203.
^
"Module-Lattice-Based Key-Encapsulation Mechanism Standard"
. 2024.
doi
:
10.6028/NIST.FIPS.203
.
- ^Schwabe, Peter."Dilithium".pq-crystals.org. Retrieved2023-08-19.
^
Schwabe, Peter.
"Dilithium"
.
pq-crystals.org
. Retrieved
2023-08-19
.
- ^"Cryptographic Suite for Algebraic Lattices, Digital Signature: Dilithium"(PDF).
^
"Cryptographic Suite for Algebraic Lattices, Digital Signature: Dilithium"
(PDF)
.
- ^"Module-Lattice-Based Digital Signature Standard". 2024.doi:10.6028/NIST.FIPS.204.
^
"Module-Lattice-Based Digital Signature Standard"
. 2024.
doi
:
10.6028/NIST.FIPS.204
.
- ^"Stateless Hash-Based Digital Signature Standard". 2024.doi:10.6028/NIST.FIPS.205.
^
"Stateless Hash-Based Digital Signature Standard"
. 2024.
doi
:
10.6028/NIST.FIPS.205
.
- ^"NIST Releases First 3 Finalized Post-Quantum Encryption Standards".NIST. 13 August 2024.
^
"NIST Releases First 3 Finalized Post-Quantum Encryption Standards"
.
NIST
. 13 August 2024.
- ^Bos, Joppe; Costello, Craig; Ducas, Léo; Mironov, Ilya; Naehrig, Michael; Nikolaenko, Valeria; Raghunathan, Ananth; Stebila, Douglas (2016-01-01)."Frodo: Take off the ring! Practical, Quantum-Secure Key Exchange from LWE".Cryptology ePrint Archive.
^
Bos, Joppe; Costello, Craig; Ducas, Léo; Mironov, Ilya; Naehrig, Michael; Nikolaenko, Valeria; Raghunathan, Ananth; Stebila, Douglas (2016-01-01).
"Frodo: Take off the ring! Practical, Quantum-Secure Key Exchange from LWE"
.
Cryptology ePrint Archive
.
- ^"FrodoKEM".frodokem.org. Retrieved2023-08-21.
^
"FrodoKEM"
.
frodokem.org
. Retrieved
2023-08-21
.
- ^"HQC".pqc-hqc.org. Retrieved2023-08-21.
^
"HQC"
.
pqc-hqc.org
. Retrieved
2023-08-21
.
- ^"Fast and Efficient Hardware Implementation of HQC"(PDF).
^
"Fast and Efficient Hardware Implementation of HQC"
(PDF)
.
- ^"NTRUOpenSourceProject/NTRUEncrypt".GitHub. Retrieved2017-04-10.
^
"NTRUOpenSourceProject/NTRUEncrypt"
.
GitHub
. Retrieved
2017-04-10
.
- ^Stebila, Douglas (26 Mar 2018)."liboqs nist-branch algorithm datasheet: kem_newhopenist".GitHub. Retrieved27 September2018.
^
Stebila, Douglas (26 Mar 2018).
"liboqs nist-branch algorithm datasheet: kem_newhopenist"
.
GitHub
. Retrieved
27 September
2018
.
- ^Bernstein, Daniel J.; Chou, Tung; Schwabe, Peter (2015-01-01)."McBits: fast constant-time code-based cryptography".Cryptology ePrint Archive.
^
Bernstein, Daniel J.; Chou, Tung; Schwabe, Peter (2015-01-01).
"McBits: fast constant-time code-based cryptography"
.
Cryptology ePrint Archive
.
- ^"Lattice Cryptography Library".Microsoft Research. 19 Apr 2016. Retrieved27 September2018.
^
"Lattice Cryptography Library"
.
Microsoft Research
. 19 Apr 2016
. Retrieved
27 September
2018
.
- ^"SIDH Library – Microsoft Research".Microsoft Research. Retrieved2017-04-10.
^
"SIDH Library – Microsoft Research"
.
Microsoft Research
. Retrieved
2017-04-10
.
- ^Feo, Luca De; Jao, David; Plût, Jérôme (2011). "Towards Quantum-Resistant Cryptosystems from Supersingular Elliptic Curve Isogenies".Post-Quantum Cryptography. Lecture Notes in Computer Science. Vol. 7071. p. 19.Bibcode:2011LNCS.7071...19J.doi:10.1007/978-3-642-25405-5_2.ISBN978-3-642-25404-8. Archived fromthe originalon 2014-05-03.
^
Feo, Luca De; Jao, David; Plût, Jérôme (2011). "Towards Quantum-Resistant Cryptosystems from Supersingular Elliptic Curve Isogenies".
Post-Quantum Cryptography
. Lecture Notes in Computer Science. Vol. 7071. p. 19.
Bibcode
:
2011LNCS.7071...19J
.
doi
:
10.1007/978-3-642-25405-5_2
.
ISBN
978-3-642-25404-8
. Archived from
the original
on 2014-05-03.
- ^"Microsoft/Picnic"(PDF).GitHub. Retrieved2018-06-27.
^
"Microsoft/Picnic"
(PDF)
.
GitHub
. Retrieved
2018-06-27
.
- ^ab"Toward Quantum Resilient Security Keys".Google Online Security Blog. Retrieved2023-08-19.
^
a
b
"Toward Quantum Resilient Security Keys"
.
Google Online Security Blog
. Retrieved
2023-08-19
.
- ^Fiedler, Rune; Janson, Christian (2024)."A Deniability Analysis of Signal's Initial Handshake PQXDH".Proceedings on Privacy Enhancing Technologies.2024(4):907–928.doi:10.56553/popets-2024-0051.ISSN2299-0984.
^
Fiedler, Rune; Janson, Christian (2024).
"A Deniability Analysis of Signal's Initial Handshake PQXDH"
.
Proceedings on Privacy Enhancing Technologies
.
2024
(4):
907–
928.
doi
:
10.56553/popets-2024-0051
.
ISSN
2299-0984
.
- ^Ehren Kret, Rolfe Schmidt (September 19, 2023)."Quantum Resistance and the Signal Protocol".Signal Foundation.
^
Ehren Kret, Rolfe Schmidt (September 19, 2023).
"Quantum Resistance and the Signal Protocol"
.
Signal Foundation
.
- ^abcApple Security Engineering and Architecture (SEAR) (February 21, 2024)."iMessage with PQ3: The new state of the art in quantum-secure messaging at scale".Apple Security Research.Apple Inc.Retrieved2024-02-22.With compromise-resilient encryption and extensive defenses against even highly sophisticated quantum attacks, PQ3 is the first messaging protocol to reach what we call Level 3 security — providing protocol protections that surpass those in all other widely deployed messaging apps.
^
a
b
c
Apple Security Engineering and Architecture (SEAR) (February 21, 2024).
"iMessage with PQ3: The new state of the art in quantum-secure messaging at scale"
.
Apple Security Research
.
Apple Inc.
Retrieved
2024-02-22
.
With compromise-resilient encryption and extensive defenses against even highly sophisticated quantum attacks, PQ3 is the first messaging protocol to reach what we call Level 3 security — providing protocol protections that surpass those in all other widely deployed messaging apps.
- ^Rossignoi, Joe (February 21, 2024)."Apple Announces 'Groundbreaking' New Security Protocol for iMessage".MacRumors. Retrieved2024-02-22.
^
Rossignoi, Joe (February 21, 2024).
"Apple Announces 'Groundbreaking' New Security Protocol for iMessage"
.
MacRumors
. Retrieved
2024-02-22
.
- ^Potuck, Michael (February 21, 2024)."Apple launching quantum computer protection for iMessage with iOS 17.4, here's what that means".9to5Mac. Retrieved2024-02-22.
^
Potuck, Michael (February 21, 2024).
"Apple launching quantum computer protection for iMessage with iOS 17.4, here's what that means"
.
9to5Mac
. Retrieved
2024-02-22
.
- ^Mahy, Rohan; Barnes, Richard (2025-03-03).ML-KEM and Hybrid Cipher Suites for Messaging Layer Security(Report). Internet Engineering Task Force.
^
Mahy, Rohan; Barnes, Richard (2025-03-03).
ML-KEM and Hybrid Cipher Suites for Messaging Layer Security
(Report). Internet Engineering Task Force.
- ^"Bouncy Castle Betas".
^
"Bouncy Castle Betas"
.
- ^"Open Quantum Safe".
^
"Open Quantum Safe"
.
- ^abAggarwal, Divesh (2018). "Quantum attacks on Bitcoin, and how to protect against them".Ledger.3:68–90.doi:10.5195/ledger.2018.127.
^
a
b
Aggarwal, Divesh (2018). "Quantum attacks on Bitcoin, and how to protect against them".
Ledger
.
3
:
68–
90.
doi
:
10.5195/ledger.2018.127
.
- ^Nejatollahi, Hamid (2019). "Post-Quantum Lattice-Based Cryptography Implementations: A Survey".ACM Computing Surveys.51(6):1–41.doi:10.1145/3292548.
^
Nejatollahi, Hamid (2019). "Post-Quantum Lattice-Based Cryptography Implementations: A Survey".
ACM Computing Surveys
.
51
(6):
1–
41.
doi
:
10.1145/3292548
.
- ^Sadot, Dan(2025)."Photonic Layer Security in High-Speed Optical Communications".Journal of Lightwave Technology.43(4). IEEE:1671–1677.doi:10.1109/JLT.2024.3522110(inactive 30 January 2026).{{cite journal}}:  CS1 maint: DOI inactive as of January 2026 (link)
^
Sadot, Dan
(2025).
"Photonic Layer Security in High-Speed Optical Communications"
.
Journal of Lightwave Technology
.
43
(4). IEEE:
1671–
1677.
doi
:
10.1109/JLT.2024.3522110
(inactive 30 January 2026).

```
{{cite journal}}
```

{{
cite journal
}}
:  CS1 maint: DOI inactive as of January 2026 (
link
)
- ^Cohen, Roi; Wohlgemuth, Eyal; Yoffe, Yaron; Yalinevich, Yarden; Attia, Ido; Yalinevich, Almog; Yehoash, Rami; Rabinovich, Aviv; Sadot, Dan (2024). "Cryptanalysis of Practical Optical Layer Security Based on Phase Masking of Mode-Locked Lasers and Multi-Homodyne Coherent Detection".Journal of Lightwave Technology.42(19). IEEE:6712–6730.Bibcode:2024JLwT...42.6712C.doi:10.1109/JLT.2024.3410646.
^
Cohen, Roi; Wohlgemuth, Eyal; Yoffe, Yaron; Yalinevich, Yarden; Attia, Ido; Yalinevich, Almog; Yehoash, Rami; Rabinovich, Aviv; Sadot, Dan (2024). "Cryptanalysis of Practical Optical Layer Security Based on Phase Masking of Mode-Locked Lasers and Multi-Homodyne Coherent Detection".
Journal of Lightwave Technology
.
42
(19). IEEE:
6712–
6730.
Bibcode
:
2024JLwT...42.6712C
.
doi
:
10.1109/JLT.2024.3410646
.
- ^abcBernstein, Daniel J.(2024-01-02)."Double encryption: Analyzing the NSA/GCHQ arguments against hybrids. #nsa #quantification #risks #complexity #costs".
^
a
b
c
Bernstein, Daniel J.
(2024-01-02).
"Double encryption: Analyzing the NSA/GCHQ arguments against hybrids. #nsa #quantification #risks #complexity #costs"
.
- ^Amico, Mirko (2019-07-08)."Experimental study of Shor's factoring algorithm using the IBM Q Experience".Physical Review A.100(1) 012305.arXiv:1903.00768.Bibcode:2019PhRvA.100a2305A.doi:10.1103/PhysRevA.100.012305.
^
Amico, Mirko (2019-07-08).
"Experimental study of Shor's factoring algorithm using the IBM Q Experience"
.
Physical Review A
.
100
(1) 012305.
arXiv
:
1903.00768
.
Bibcode
:
2019PhRvA.100a2305A
.
doi
:
10.1103/PhysRevA.100.012305
.
- ^Yan, Bao; Tan, Ziqi; Wei, Shijie; Jiang, Haocong; Wang, Weilong; Wang, Hong; Luo, Lan; Duan, Qianheng; Liu, Yiting; Shi, Wenhao; Fei, Yangyang; Meng, Xiangdong; Han, Yu; Shan, Zheng; Chen, Jiachen; Zhu, Xuhao; Zhang, Chuanyu; Jin, Feitong; Li, Hekang; Song, Chao; Wang, Zhen; Ma, Zhi; Wang, H.; Long, Gui-Lu (2022). "Factoring integers with sublinear resources on a superconducting quantum processor".arXiv:2212.12372[quant-ph].
^
Yan, Bao; Tan, Ziqi; Wei, Shijie; Jiang, Haocong; Wang, Weilong; Wang, Hong; Luo, Lan; Duan, Qianheng; Liu, Yiting; Shi, Wenhao; Fei, Yangyang; Meng, Xiangdong; Han, Yu; Shan, Zheng; Chen, Jiachen; Zhu, Xuhao; Zhang, Chuanyu; Jin, Feitong; Li, Hekang; Song, Chao; Wang, Zhen; Ma, Zhi; Wang, H.; Long, Gui-Lu (2022). "Factoring integers with sublinear resources on a superconducting quantum processor".
arXiv
:
2212.12372
[
quant-ph
].
- ^Schuld, Maria (2025-04-16)."Period finding: A problem at the heart of quantum computing".Pennylane. Retrieved2026-04-30.
^
Schuld, Maria (2025-04-16).
"Period finding: A problem at the heart of quantum computing"
.
Pennylane
. Retrieved
2026-04-30
.
- ^"The Concept of Branchial Graphs".Wolfram Physics Project. Retrieved2026-04-30.
^
"The Concept of Branchial Graphs"
.
Wolfram Physics Project
. Retrieved
2026-04-30
.
- ^Fridman, Lex (2020-09-18)."The Hope for Quantum Computers | Stephen Wolfram and Lex Fridman".YouTube. Retrieved2026-04-30.
^
Fridman, Lex (2020-09-18).
"The Hope for Quantum Computers | Stephen Wolfram and Lex Fridman"
.
YouTube
. Retrieved
2026-04-30
.
- ^Schneier, Bruce (2013-09-05)."The NSA Is Breaking Most Encryption on the Internet".Schneier on Security. Retrieved2026-04-30.
^
Schneier, Bruce (2013-09-05).
"The NSA Is Breaking Most Encryption on the Internet"
.
Schneier on Security
. Retrieved
2026-04-30
.

## Further reading

Further reading
[
edit
]
- Bagirovs, Emils; Provodin, Grigory; Sipola, Tuomo; Hautamäki, Jari (2024). "Applications of Post-quantum Cryptography".European Conference on Cyber Warfare and Security.23(1):49–57.arXiv:2406.13258.doi:10.34190/eccws.23.1.2247.
Bagirovs, Emils; Provodin, Grigory; Sipola, Tuomo; Hautamäki, Jari (2024). "Applications of Post-quantum Cryptography".
European Conference on Cyber Warfare and Security
.
23
(1):
49–
57.
arXiv
:
2406.13258
.
doi
:
10.34190/eccws.23.1.2247
.
- Bavdekar, Ritik; Chopde, Eashan Jayant; Bhatia, Ashutosh; Tiwari, Kamlesh; Daniel, Sandeep Joshua (2022). "Post Quantum Cryptography: Techniques, Challenges, Standardization, and Directions for Future Research".arXiv:2202.02826[cs.CR].
Bavdekar, Ritik; Chopde, Eashan Jayant; Bhatia, Ashutosh; Tiwari, Kamlesh; Daniel, Sandeep Joshua (2022). "Post Quantum Cryptography: Techniques, Challenges, Standardization, and Directions for Future Research".
arXiv
:
2202.02826
[
cs.CR
].
- Bavdekar, Ritik; Jayant Chopde, Eashan; Agrawal, Ankit; Bhatia, Ashutosh; Tiwari, Kamlesh (2023). "Post Quantum Cryptography: A Review of Techniques, Challenges and Standardizations".2023 International Conference on Information Networking (ICOIN). pp.146–151.doi:10.1109/ICOIN56518.2023.10048976.ISBN978-1-6654-6268-6.
Bavdekar, Ritik; Jayant Chopde, Eashan; Agrawal, Ankit; Bhatia, Ashutosh; Tiwari, Kamlesh (2023). "Post Quantum Cryptography: A Review of Techniques, Challenges and Standardizations".
2023 International Conference on Information Networking (ICOIN)
. pp.
146–
151.
doi
:
10.1109/ICOIN56518.2023.10048976
.
ISBN
978-1-6654-6268-6
.
- Bernstein, Daniel J.; Buchmann, Johannes; Dahmen, Erik, eds. (2008).Post-Quantum Cryptography. Springer. p. 245.ISBN978-3-540-88701-0.
Bernstein, Daniel J.; Buchmann, Johannes; Dahmen, Erik, eds. (2008).
Post-Quantum Cryptography
. Springer. p. 245.
ISBN
978-3-540-88701-0
.
- Bernstein, Daniel J.; Lange, Tanja (2017)."Post-quantum cryptography".Nature.549(7671):188–194.Bibcode:2017Natur.549..188B.doi:10.1038/nature23461.PMID28905891.
Bernstein, Daniel J.; Lange, Tanja (2017).
"Post-quantum cryptography"
.
Nature
.
549
(7671):
188–
194.
Bibcode
:
2017Natur.549..188B
.
doi
:
10.1038/nature23461
.
PMID
28905891
.
- Buchmann, Johannes A.; Butin, Denis; Göpfert, Florian; Petzoldt, Albrecht (2016)."Post-Quantum Cryptography: State of the Art".The New Codebreakers: Essays Dedicated to David Kahn on the Occasion of His 85th Birthday. Springer. pp.88–108.doi:10.1007/978-3-662-49301-4_6.ISBN978-3-662-49301-4.
Buchmann, Johannes A.; Butin, Denis; Göpfert, Florian; Petzoldt, Albrecht (2016).
"Post-Quantum Cryptography: State of the Art"
.
The New Codebreakers: Essays Dedicated to David Kahn on the Occasion of His 85th Birthday
. Springer. pp.
88–
108.
doi
:
10.1007/978-3-662-49301-4_6
.
ISBN
978-3-662-49301-4
.
- Campagna, M.; Hardjono, T.; Pintsov, L.; Romansky, B.; and Yu, T. "Kerberos Revisited: Quantum-Safe Authentication". ETSI Quantum-Safe-Crypto Workshop. September 26, 2013.
Campagna, M.; Hardjono, T.; Pintsov, L.; Romansky, B.; and Yu, T. "
Kerberos Revisited: Quantum-Safe Authentication
". ETSI Quantum-Safe-Crypto Workshop. September 26, 2013.
- Campagna, Matt; LaMacchia, Brian; Ott, David (2021). "Post Quantum Cryptography: Readiness Challenges and the Approaching Storm".Computing Community Consortium.arXiv:2101.01269.
Campagna, Matt; LaMacchia, Brian; Ott, David (2021). "Post Quantum Cryptography: Readiness Challenges and the Approaching Storm".
Computing Community Consortium
.
arXiv
:
2101.01269
.
- Chase, Melissa; Derler, David; Goldfeder, Steven; Orlandi, Claudio; Ramacher, Sebastian; Rechberger, Christian; Slamanig, Daniel; Zaverucha, Greg (29 November 2017).The Picnic Signature Scheme Design DocumentVersion 1.0.
Chase, Melissa; Derler, David; Goldfeder, Steven; Orlandi, Claudio; Ramacher, Sebastian; Rechberger, Christian; Slamanig, Daniel; Zaverucha, Greg (29 November 2017).
The Picnic Signature Scheme Design Document
Version 1.0.
- Dam, Duc-Thuan; Tran, Thai-Ha; Hoang, Van-Phuc; Pham, Cong-Kha; Hoang, Trong-Thuc (2023)."A Survey of Post-Quantum Cryptography: Start of a New Race".Cryptography.7(3): 40.doi:10.3390/cryptography7030040.
Dam, Duc-Thuan; Tran, Thai-Ha; Hoang, Van-Phuc; Pham, Cong-Kha; Hoang, Trong-Thuc (2023).
"A Survey of Post-Quantum Cryptography: Start of a New Race"
.
Cryptography
.
7
(3): 40.
doi
:
10.3390/cryptography7030040
.
- Jao, David (September 19, 2011).Isogenies in a Quantum World;Archived2014-05-02 at theWayback Machine. University of Waterloo.
Jao, David (September 19, 2011).
Isogenies in a Quantum World
;
Archived
2014-05-02 at the
Wayback Machine
. University of Waterloo.
- Joseph, David; Misoczki, Rafael; Manzano, Marc; Tricot, Joe; Pinuaga, Fernando Dominguez; Lacombe, Olivier; Leichenauer, Stefan; Hidary, Jack; Venables, Phil; Hansen, Royal (2022). "Transitioning organizations to post-quantum cryptography".Nature.605(7909):237–243.Bibcode:2022Natur.605..237J.doi:10.1038/s41586-022-04623-2.PMID35546191.
Joseph, David; Misoczki, Rafael; Manzano, Marc; Tricot, Joe; Pinuaga, Fernando Dominguez; Lacombe, Olivier; Leichenauer, Stefan; Hidary, Jack; Venables, Phil; Hansen, Royal (2022). "Transitioning organizations to post-quantum cryptography".
Nature
.
605
(7909):
237–
243.
Bibcode
:
2022Natur.605..237J
.
doi
:
10.1038/s41586-022-04623-2
.
PMID
35546191
.
- Kret, Ehren; Rolfe Schmidt (2024-01-23) [2023-05-24].The PQXDH Key Agreement Protocol Specification, Revision 3.
Kret, Ehren; Rolfe Schmidt (2024-01-23) [2023-05-24].
The PQXDH Key Agreement Protocol Specification
, Revision 3.
- Kumar, Manoj; Pattnaik, Pratap (2020). "Post Quantum Cryptography – an overview: (Invited Paper)".2020 IEEE High Performance Extreme Computing Conference. pp.1–9.doi:10.1109/HPEC43674.2020.9286147.ISBN978-1-7281-9219-2.
Kumar, Manoj; Pattnaik, Pratap (2020). "Post Quantum Cryptography – an overview: (Invited Paper)".
2020 IEEE High Performance Extreme Computing Conference
. pp.
1–
9.
doi
:
10.1109/HPEC43674.2020.9286147
.
ISBN
978-1-7281-9219-2
.
- Li, Silong; Chen, Yuxiang; Chen, Lin; Liao, Jing; Kuang, Chanchan; Li, Kuanching; Liang, Wei; Xiong, Naixue (2023)."Post-Quantum Security: Opportunities and Challenges".Sensors.23(21): 8744.Bibcode:2023Senso..23.8744L.doi:10.3390/s23218744.PMC10648643.PMID37960442.
Li, Silong; Chen, Yuxiang; Chen, Lin; Liao, Jing; Kuang, Chanchan; Li, Kuanching; Liang, Wei; Xiong, Naixue (2023).
"Post-Quantum Security: Opportunities and Challenges"
.
Sensors
.
23
(21): 8744.
Bibcode
:
2023Senso..23.8744L
.
doi
:
10.3390/s23218744
.
PMC
10648643
.
PMID
37960442
.
- Lyubashevsky, Vadim; Chris Peikert; Oded Regev. "On Ideal Lattices and Learning with Errors Over Rings".
Lyubashevsky, Vadim; Chris Peikert; Oded Regev. "
On Ideal Lattices and Learning with Errors Over Rings
".
- Mamatha, G S; Dimri, Namya; Sinha, Rasha (2024). "Post-Quantum Cryptography: Securing Digital Communication in the Quantum Era".arXiv:2403.11741[cs.CR].
Mamatha, G S; Dimri, Namya; Sinha, Rasha (2024). "Post-Quantum Cryptography: Securing Digital Communication in the Quantum Era".
arXiv
:
2403.11741
[
cs.CR
].
- Rawal, Bharat S.; Curry, Peter J. (2024)."Challenges and opportunities on the horizon of post-quantum cryptography".APL Quantum.1(2) 026110.doi:10.1063/5.0198344.
Rawal, Bharat S.; Curry, Peter J. (2024).
"Challenges and opportunities on the horizon of post-quantum cryptography"
.
APL Quantum
.
1
(2) 026110.
doi
:
10.1063/5.0198344
.
- Richter, Maximilian; Bertram, Magdalena; Seidensticker, Jasper; Tschache, Alexander (2022)."A Mathematical Perspective on Post-Quantum Cryptography".Mathematics.10(15): 2579.doi:10.3390/math10152579.
Richter, Maximilian; Bertram, Magdalena; Seidensticker, Jasper; Tschache, Alexander (2022).
"A Mathematical Perspective on Post-Quantum Cryptography"
.
Mathematics
.
10
(15): 2579.
doi
:
10.3390/math10152579
.
- Sood, Neerav (2024)."Cryptography in Post Quantum Computing Era".SSRN Electronic Journal.doi:10.2139/ssrn.4705470.
Sood, Neerav (2024).
"Cryptography in Post Quantum Computing Era"
.
SSRN Electronic Journal
.
doi
:
10.2139/ssrn.4705470
.
- Singh, Balvinder; Ahateshaam, Md; Lahiri, Abhisweta; Sagar, Anil Kumar (2024). "Future of Cryptography in the Era of Quantum Computing".Innovations in Electrical and Electronic Engineering. Lecture Notes in Electrical Engineering. Vol. 1115. pp.13–31.doi:10.1007/978-981-99-8661-3_2.ISBN978-981-99-8660-6.
Singh, Balvinder; Ahateshaam, Md; Lahiri, Abhisweta; Sagar, Anil Kumar (2024). "Future of Cryptography in the Era of Quantum Computing".
Innovations in Electrical and Electronic Engineering
. Lecture Notes in Electrical Engineering. Vol. 1115. pp.
13–
31.
doi
:
10.1007/978-981-99-8661-3_2
.
ISBN
978-981-99-8660-6
.
- Yalamuri, Gagan; Honnavalli, Prasad; Eswaran, Sivaraman (2022)."A Review of the Present Cryptographic Arsenal to Deal with Post-Quantum Threats".Procedia Computer Science.215:834–845.doi:10.1016/j.procs.2022.12.086.
Yalamuri, Gagan; Honnavalli, Prasad; Eswaran, Sivaraman (2022).
"A Review of the Present Cryptographic Arsenal to Deal with Post-Quantum Threats"
.
Procedia Computer Science
.
215
:
834–
845.
doi
:
10.1016/j.procs.2022.12.086
.

## External links

External links
[
edit
]
- PQCrypto, the post-quantum cryptography conference
PQCrypto, the post-quantum cryptography conference
- ETSI Quantum Secure Standards Effort
ETSI Quantum Secure Standards Effort
- NIST's Post-Quantum crypto Project
NIST's Post-Quantum crypto Project
- PQCrypto Usage & Deployment
PQCrypto Usage & Deployment
- ISO 27001 Certification Cost
ISO 27001 Certification Cost
- ISO 22301:2019 – Security and Resilience in the United States
ISO 22301:2019 – Security and Resilience in the United States
- Vulnerability Score of Common Encryption Algorithms
Vulnerability Score of Common Encryption Algorithms
- DilithiumandSPHINCS+, explanation and demonstration in Excel (without macros) by Tim Wambach
Dilithium
and
SPHINCS+
, explanation and demonstration in Excel (without macros) by Tim Wambach

<!-- table omitted -->

- v
v
- t
t
- e
e
Quantum mechanics
Background
- Introduction
Introduction
- HistoryTimeline
History
- Timeline
Timeline
- Classical mechanics
Classical mechanics
- Old quantum theory
Old quantum theory
- Glossary
Glossary
Fundamentals
- Born rule
Born rule
- Bra–ket notation
Bra–ket notation
- Complementarity
Complementarity
- Density matrix
Density matrix
- Energy levelGround stateExcited stateDegenerate levelsZero-point energy
Energy level
- Ground state
Ground state
- Excited state
Excited state
- Degenerate levels
Degenerate levels
- Zero-point energy
Zero-point energy
- Entanglement
Entanglement
- Hamiltonian
Hamiltonian
- Interference
Interference
- Decoherence
Decoherence
- Measurement
Measurement
- Nonlocality
Nonlocality
- Quantum statequantum jump
Quantum state
- quantum jump
quantum jump
- Superposition
Superposition
- Tunnelling
Tunnelling
- Scattering theory
Scattering theory
- Symmetry in quantum mechanics
Symmetry in quantum mechanics
- Uncertainty
Uncertainty
- Wave functionCollapseWave–particle dualityUniversal wavefunction
Wave function
- Collapse
Collapse
- Wave–particle duality
Wave–particle duality
- Universal wavefunction
Universal wavefunction
Formulations
- Formulations
Formulations
- Heisenberg
Heisenberg
- Interaction
Interaction
- Matrix mechanics
Matrix mechanics
- Schrödinger
Schrödinger
- Path integral formulation
Path integral formulation
- Phase space
Phase space
Equations
- Klein–Gordon
Klein–Gordon
- Dirac
Dirac
- Weyl
Weyl
- Majorana
Majorana
- Rarita–Schwinger
Rarita–Schwinger
- Pauli
Pauli
- Rydberg
Rydberg
- Schrödinger
Schrödinger
Interpretations
- Bayesian
Bayesian
- Consciousness causes collapse
Consciousness causes collapse
- Consistent histories
Consistent histories
- Copenhagen
Copenhagen
- de Broglie–Bohm
de Broglie–Bohm
- Ensemble
Ensemble
- Hidden-variableLocalSuperdeterminism
Hidden-variable
- LocalSuperdeterminism
Local
- Superdeterminism
Superdeterminism
- Many-worlds
Many-worlds
- Objective collapse
Objective collapse
- Quantum logic
Quantum logic
- Relational
Relational
- Transactional
Transactional
Experiments
- Bell test
Bell test
- Davisson–Germer
Davisson–Germer
- Delayed-choice quantum eraser
Delayed-choice quantum eraser
- Double-slit
Double-slit
- Franck–Hertz
Franck–Hertz
- Mach–Zehnder interferometer
Mach–Zehnder interferometer
- Elitzur–Vaidman
Elitzur–Vaidman
- Popper
Popper
- Quantum eraser
Quantum eraser
- Stern–Gerlach
Stern–Gerlach
- Wheeler's delayed choice
Wheeler's delayed choice
Science
- Quantum biology
Quantum biology
- Quantum chemistry
Quantum chemistry
- Quantum chaos
Quantum chaos
- Quantum cosmology
Quantum cosmology
- Quantum differential calculus
Quantum differential calculus
- Quantum dynamics
Quantum dynamics
- Quantum geometry
Quantum geometry
- Quantum measurement problem
Quantum measurement problem
- Quantum mind
Quantum mind
- Quantum stochastic calculus
Quantum stochastic calculus
- Quantum spacetime
Quantum spacetime
Technology
- Quantum algorithms
Quantum algorithms
- Quantum amplifier
Quantum amplifier
- Quantum bus
Quantum bus
- Quantum cellular automataQuantum finite automata
Quantum cellular automata
- Quantum finite automata
Quantum finite automata
- Quantum channel
Quantum channel
- Quantum circuit
Quantum circuit
- Quantum complexity theory
Quantum complexity theory
- Quantum computingTimeline
Quantum computing
- Timeline
Timeline
- Quantum cryptography
Quantum cryptography
- Quantum electronics
Quantum electronics
- Quantum error correction
Quantum error correction
- Quantum imaging
Quantum imaging
- Quantum image processing
Quantum image processing
- Quantum information
Quantum information
- Quantum key distribution
Quantum key distribution
- Quantum logic
Quantum logic
- Quantum logic gates
Quantum logic gates
- Quantum machine
Quantum machine
- Quantum machine learning
Quantum machine learning
- Quantum metamaterial
Quantum metamaterial
- Quantum metrology
Quantum metrology
- Quantum network
Quantum network
- Quantum neural network
Quantum neural network
- Quantum optics
Quantum optics
- Quantum programming
Quantum programming
- Quantum sensing
Quantum sensing
- Quantum simulator
Quantum simulator
- Quantum teleportation
Quantum teleportation
Extensions
- Quantum fluctuation
Quantum fluctuation
- Casimir effect
Casimir effect
- Quantum statistical mechanics
Quantum statistical mechanics
- Quantum field theoryHistory
Quantum field theory
- History
History
- Quantum gravity
Quantum gravity
- Relativistic quantum mechanics
Relativistic quantum mechanics
Related
- Schrödinger's catin popular culture
Schrödinger's cat
- in popular culture
in popular culture
- Wigner's friend
Wigner's friend
- EPR paradox
EPR paradox
- Quantum mysticism
Quantum mysticism
- Category
Category

<!-- table omitted -->

- v
v
- t
t
- e
e
Quantum information science
General
- DiVincenzo's criteria
DiVincenzo's criteria
- NISQ era
NISQ era
- Quantum computingtimeline
Quantum computing
- timeline
timeline
- Quantum information
Quantum information
- Quantum programming
Quantum programming
- Quantum simulation
Quantum simulation
- Qubitphysical vs. logical
Qubit
- physical vs. logical
physical vs. logical
- Quantum processorscloud-based
Quantum processors
- cloud-based
cloud-based
Theorems
- Bell's
Bell's
- Eastin–Knill
Eastin–Knill
- Gleason's
Gleason's
- Gottesman–Knill
Gottesman–Knill
- Holevo's
Holevo's
- No-broadcasting
No-broadcasting
- No-cloning
No-cloning
- No-communication
No-communication
- No-deleting
No-deleting
- No-hiding
No-hiding
- No-teleportation
No-teleportation
- PBR
PBR
- Quantum speed limit
Quantum speed limit
- Threshold
Threshold
- Solovay–Kitaev
Solovay–Kitaev
- Schrödinger-HJW
Schrödinger-HJW
Quantum
communication
- Classical capacityentanglement-assistedquantum capacity
Classical capacity
- entanglement-assisted
entanglement-assisted
- quantum capacity
quantum capacity
- Entanglement distillation
Entanglement distillation
- Entanglement swapping
Entanglement swapping
- Monogamy of entanglement
Monogamy of entanglement
- LOCC
LOCC
- Quantum channelquantum network
Quantum channel
- quantum network
quantum network
- State purification
State purification
- Quantum teleportationquantum energy teleportationquantum gate teleportation
Quantum teleportation
- quantum energy teleportation
quantum energy teleportation
- quantum gate teleportation
quantum gate teleportation
- Superdense coding
Superdense coding

<!-- table omitted -->

Quantum cryptography
- Decoy state
Decoy state
- Hidden matching
Hidden matching
- Post-quantum cryptography
Post-quantum cryptography
- Quantum coin flipping
Quantum coin flipping
- Quantum money
Quantum money
- Quantum key distributionBB84SARG04other protocols
Quantum key distribution
- BB84
BB84
- SARG04
SARG04
- other protocols
other protocols
- Quantum secret sharing
Quantum secret sharing
Quantum algorithms
- Algorithmic cooling
Algorithmic cooling
- Amplitude amplification
Amplitude amplification
- Bernstein–Vazirani
Bernstein–Vazirani
- BHT
BHT
- Boson sampling
Boson sampling
- Deutsch–Jozsa
Deutsch–Jozsa
- Grover's
Grover's
- HHL
HHL
- Hidden subgroup
Hidden subgroup
- Magic state distillation
Magic state distillation
- Quantum annealing
Quantum annealing
- Quantum counting
Quantum counting
- Quantum Fourier transform
Quantum Fourier transform
- Quantum optimization
Quantum optimization
- Quantum phase estimation
Quantum phase estimation
- Shor's
Shor's
- Simon's
Simon's
- VQE
VQE
Quantum
complexity theory
- BQP
BQP
- DQC1
DQC1
- EQP
EQP
- QIP
QIP
- QMA
QMA
- PostBQP
PostBQP
Quantum
processor benchmarks
- Quantum supremacy
Quantum supremacy
- Quantum volume
Quantum volume
- QC scaling laws
QC scaling laws
- Randomized benchmarkingXEB
Randomized benchmarking
- XEB
XEB
- Relaxation timesT1T2
Relaxation times
- T1
T
1
- T2
T
2
Quantum
computing models
- Adiabatic quantum computation
Adiabatic quantum computation
- Continuous-variable quantum information
Continuous-variable quantum information
- One-way quantum computercluster state
One-way quantum computer
- cluster state
cluster state
- Quantum circuitquantum logic gate
Quantum circuit
- quantum logic gate
quantum logic gate
- Quantum machine learningquantum neural network
Quantum machine learning
- quantum neural network
quantum neural network
- Quantum Turing machine
Quantum Turing machine
- Topological quantum computer
Topological quantum computer
- Hamiltonian quantum computation
Hamiltonian quantum computation
Quantum
error correction
- Codes5 qubitCSSGKPquantum convolutionalstabilizerShorBacon–ShorSteaneToricgnu
Codes
- 5 qubit
5 qubit
- CSS
CSS
- GKP
GKP
- quantum convolutional
quantum convolutional
- stabilizer
stabilizer
- Shor
Shor
- Bacon–Shor
Bacon–Shor
- Steane
Steane
- Toric
Toric
- gnu
gnu
- Entanglement-assisted
Entanglement-assisted
Physical
implementations

<!-- table omitted -->

Quantum optics
- Cavity QED
Cavity QED
- Circuit QED
Circuit QED
- Linear optical QC
Linear optical QC
- KLM protocol
KLM protocol
Ultracold atoms
- Neutral atom QC
Neutral atom QC
- Trapped-ion QC
Trapped-ion QC
Spin
-based
- Kane QC
Kane QC
- Spin qubit QC
Spin qubit QC
- NV center
NV center
- NMR QC
NMR QC
Superconducting
- Charge qubit
Charge qubit
- Flux qubit
Flux qubit
- Phase qubit
Phase qubit
- Transmon
Transmon
Quantum
programming
- OpenQASM–Qiskit–IBM QX
OpenQASM
–
Qiskit
–
IBM QX
- Quil–Forest/Rigetti QCS
Quil
–
Forest/Rigetti QCS
- Cirq
Cirq
- Q#
Q#
- libquantum
libquantum
- many others...
many others...
- Quantum information science
Quantum information science
- Quantum mechanics topics
Quantum mechanics topics
NewPP limit report
Parsed by mw‐web.codfw.main‐7dbdc7fd5b‐rz4ql
Cached time: 20260628223911
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.690 seconds
Real time usage: 0.854 seconds
Preprocessor visited node count: 7350/1000000
Revision size: 86296/2097152 bytes
Post‐expand include size: 351119/2097152 bytes
Template argument size: 3256/2097152 bytes
Highest expansion depth: 12/100
Expensive parser function count: 14/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 501729/5000000 bytes
Lua time usage: 0.437/10.000 seconds
Lua memory usage: 6948567/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  700.072      1 -total
 53.82%  376.786      1 Template:Reflist
 23.95%  167.673     56 Template:Cite_web
 12.40%   86.811     32 Template:Cite_journal
  9.58%   67.098     24 Template:Cite_book
  7.37%   51.627      4 Template:Navbox
  6.70%   46.925      1 Template:Quantum_mechanics_topics
  6.66%   46.602      1 Template:Short_description
  4.84%   33.918      3 Template:Citation_needed
  4.28%   29.982      9 Template:Citation
Render ID 2e7a59f2-7342-11f1-84dc-07192db9617f
Saved in parser cache with key enwiki:pcache:26605226:|#|:idhash:canonical and timestamp 20260628223911 and revision id 1361591475. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Post-quantum_cryptography&oldid=1361591475
"
Categories
:
- Post-quantum cryptography
Post-quantum cryptography
- Cryptography
Cryptography
Hidden categories:
- CS1 maint: work parameter with ISBN
CS1 maint: work parameter with ISBN
- CS1 maint: DOI inactive as of January 2026
CS1 maint: DOI inactive as of January 2026
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from August 2015
Articles with unsourced statements from August 2015
- Articles with unsourced statements from March 2022
Articles with unsourced statements from March 2022
- Articles to be expanded from March 2026
Articles to be expanded from March 2026
- All articles to be expanded
All articles to be expanded
- Articles with unsourced statements from February 2024
Articles with unsourced statements from February 2024
- Webarchive template wayback links
Webarchive template wayback links