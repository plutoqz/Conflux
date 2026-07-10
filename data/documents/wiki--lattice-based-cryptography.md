<!-- source: https://en.wikipedia.org/wiki/Lattice-based_cryptography -->
# Lattice-based cryptography

> Source: https://en.wikipedia.org/wiki/Lattice-based_cryptography
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Cryptographic primitives that involve lattices
Lattice-based cryptographyis the generic term for constructions ofcryptographic primitivesthat involvelattices, either in the construction itself or in the security proof. Lattice-based constructions support important standards ofpost-quantum cryptography.[1]Unlike more widely used and known public-key schemes such as theRSA,Diffie-Hellmanorelliptic-curvecryptosystems—which could, theoretically, be defeated usingShor's algorithmon aquantum computer—some lattice-based constructions appear to be resistant to attack by both classical and quantum computers. Furthermore, many lattice-based constructions are considered to be secure under theassumptionthat certain well-studied computationallattice problemscannot be solved efficiently.

Lattice-based cryptography
is the generic term for constructions of
cryptographic primitives
that involve
lattices
, either in the construction itself or in the security proof. Lattice-based constructions support important standards of
post-quantum cryptography
.
[
1
]
Unlike more widely used and known public-key schemes such as the
RSA
,
Diffie-Hellman
or
elliptic-curve
cryptosystems—which could, theoretically, be defeated using
Shor's algorithm
on a
quantum computer
—some lattice-based constructions appear to be resistant to attack by both classical and quantum computers. Furthermore, many lattice-based constructions are considered to be secure under the
assumption
that certain well-studied computational
lattice problems
cannot be solved efficiently.
In 2024NISTannounced the Module-Lattice-Based Digital Signature Standard for post-quantum cryptography.[2]

In 2024
NIST
announced the Module-Lattice-Based Digital Signature Standard for post-quantum cryptography.
[
2
]

## History

History
[
edit
]
In 1996,Miklós Ajtaiintroduced the first lattice-based cryptographic construction whose security could be based on the hardness of well-studied lattice problems,[3]andCynthia Dworkshowed that a certain average-case lattice problem, known asshort integer solutions(SIS), is at least as hard to solve as aworst-caselattice problem.[4]She then showed acryptographic hash functionwhose security is equivalent to the computational hardness of SIS.

In 1996,
Miklós Ajtai
introduced the first lattice-based cryptographic construction whose security could be based on the hardness of well-studied lattice problems,
[
3
]
and
Cynthia Dwork
showed that a certain average-case lattice problem, known as
short integer solutions
(SIS), is at least as hard to solve as a
worst-case
lattice problem.
[
4
]
She then showed a
cryptographic hash function
whose security is equivalent to the computational hardness of SIS.
In 1998,Jeffrey Hoffstein,Jill Pipher, andJoseph H. Silvermanintroduced a lattice-basedpublic-key encryptionscheme, known asNTRU.[5]However, their scheme is not known to be at least as hard as solving a worst-case lattice problem.

In 1998,
Jeffrey Hoffstein
,
Jill Pipher
, and
Joseph H. Silverman
introduced a lattice-based
public-key encryption
scheme, known as
NTRU
.
[
5
]
However, their scheme is not known to be at least as hard as solving a worst-case lattice problem.
The first lattice-based public-key encryption scheme whose security was proven under worst-case hardness assumptions was introduced byOded Regevin 2005,[6]together with thelearning with errorsproblem (LWE). Since then, much follow-up work has focused on improving Regev's security proof[7][8]and improving the efficiency of the original scheme.[9][10][11][12]Much more work has been devoted to constructing additional cryptographic primitives based on LWE and related problems. For example, in 2009,Craig Gentryintroduced the firstfully homomorphic encryptionscheme, which was based on a lattice problem.[13]

The first lattice-based public-key encryption scheme whose security was proven under worst-case hardness assumptions was introduced by
Oded Regev
in 2005,
[
6
]
together with the
learning with errors
problem (LWE). Since then, much follow-up work has focused on improving Regev's security proof
[
7
]
[
8
]
and improving the efficiency of the original scheme.
[
9
]
[
10
]
[
11
]
[
12
]
Much more work has been devoted to constructing additional cryptographic primitives based on LWE and related problems. For example, in 2009,
Craig Gentry
introduced the first
fully homomorphic encryption
scheme, which was based on a lattice problem.
[
13
]

## Mathematical background

Mathematical background
[
edit
]
Inlinear algebra, alatticeL⊂Rn{\displaystyle L\subset \mathbb {R} ^{n}}is the set of all integer linear combinations of vectors from abasis{b1,…,bn}{\displaystyle \{\mathbf {b} _{1},\ldots ,\mathbf {b} _{n}\}}ofRn{\displaystyle \mathbb {R} ^{n}}. In other words,L={∑aibi:ai∈Z}.{\displaystyle L={\Big \{}\sum a_{i}\mathbf {b} _{i}:a_{i}\in \mathbb {Z} {\Big \}}.}For example,Zn{\displaystyle \mathbb {Z} ^{n}}is a lattice, generated by thestandard basisforRn{\displaystyle \mathbb {R} ^{n}}. Crucially, the basis for a lattice is not unique. For example, the vectors(3,1,4){\displaystyle (3,1,4)},(1,5,9){\displaystyle (1,5,9)}, and(2,−1,0){\displaystyle (2,-1,0)}form an alternative basis forZ3{\displaystyle \mathbb {Z} ^{3}}.

In
linear algebra
, a
lattice
L
⊂
⊂
R
n
{\displaystyle L\subset \mathbb {R} ^{n}}
is the set of all integer linear combinations of vectors from a
basis
{
b
1
,
…
…
,
b
n
}
{\displaystyle \{\mathbf {b} _{1},\ldots ,\mathbf {b} _{n}\}}
of
R
n
{\displaystyle \mathbb {R} ^{n}}
. In other words,
L
=
{
∑
∑
a
i
b
i
:
a
i
∈
∈
Z
}
.
{\displaystyle L={\Big \{}\sum a_{i}\mathbf {b} _{i}:a_{i}\in \mathbb {Z} {\Big \}}.}
For example,
Z
n
{\displaystyle \mathbb {Z} ^{n}}
is a lattice, generated by the
standard basis
for
R
n
{\displaystyle \mathbb {R} ^{n}}
. Crucially, the basis for a lattice is not unique. For example, the vectors
(
3
,
1
,
4
)
{\displaystyle (3,1,4)}
,
(
1
,
5
,
9
)
{\displaystyle (1,5,9)}
, and
(
2
,
−
−
1
,
0
)
{\displaystyle (2,-1,0)}
form an alternative basis for
Z
3
{\displaystyle \mathbb {Z} ^{3}}
.
The most important lattice-based computational problem is theshortest vector problem(SVP or sometimes GapSVP), which asks for an approximate minimal Euclidean length of a non-zero lattice vector. This problem is thought to be hard to solve efficiently, even with approximation factors that are polynomial inn{\displaystyle n}, and even with a quantum computer. Many (though not all) lattice-based cryptographic constructions are known to be secure if SVP is in fact hard in this regime.

The most important lattice-based computational problem is the
shortest vector problem
(SVP or sometimes GapSVP), which asks for an approximate minimal Euclidean length of a non-zero lattice vector. This problem is thought to be hard to solve efficiently, even with approximation factors that are polynomial in
n
{\displaystyle n}
, and even with a quantum computer. Many (though not all) lattice-based cryptographic constructions are known to be secure if SVP is in fact hard in this regime.

## Selected lattice-based schemes

Selected lattice-based schemes
[
edit
]
This section presents selected lattice-based schemes, grouped by primitive.

This section presents selected lattice-based schemes, grouped by primitive.

### Encryption

Encryption
[
edit
]
Selected schemes for the purpose of encryption:

Selected schemes for the purpose of encryption:
- GGH encryption scheme, which is based in the closest vector problem (CVP). In 1999, Nguyen published a critical flaw in the scheme's design.[14]
GGH encryption scheme
, which is based in the closest vector problem (CVP). In 1999, Nguyen published a critical flaw in the scheme's design.
[
14
]
- NTRUEncrypt.
NTRUEncrypt
.

### Homomorphic encryption

Homomorphic encryption
[
edit
]
Selected schemes for the purpose ofhomomorphic encryption:

Selected schemes for the purpose of
homomorphic encryption
:
- Gentry's original scheme.[13]
Gentry's original scheme.
[
13
]
- Brakerski and Vaikuntanathan.[15][16]
Brakerski and Vaikuntanathan.
[
15
]
[
16
]

### Hash functions

Hash functions
[
edit
]
Selected lattice-based cryptographic schemes for the purpose of hashing:

Selected lattice-based cryptographic schemes for the purpose of hashing:
- SWIFFT.
SWIFFT
.
- Lattice Based Hash Function (LASH).[17][18]
Lattice Based Hash Function (LASH).
[
17
]
[
18
]

### Key exchange

Key exchange
[
edit
]
Selected schemes for the purpose of key exchange, also called key establishment, key encapsulation and key encapsulation mechanism (KEM):

Selected schemes for the purpose of key exchange, also called key establishment, key encapsulation and key encapsulation mechanism (KEM):
- CRYSTALS-Kyber,[19]which is built upon module learning with errors (module-LWE). Kyber was selected for standardization by the NIST in 2023.[1]In August 2023, NIST published FIPS 203 (Initial Public Draft), and started referring to their Kyber version as Module-Lattice-based Key Encapsulation Mechanism (ML-KEM).[20]
CRYSTALS-Kyber
,
[
19
]
which is built upon module learning with errors (module-LWE). Kyber was selected for standardization by the NIST in 2023.
[
1
]
In August 2023, NIST published FIPS 203 (Initial Public Draft), and started referring to their Kyber version as Module-Lattice-based Key Encapsulation Mechanism (ML-KEM).
[
20
]
- FrodoKEM,[21][22]a scheme based on the learning with errors (LWE) problem. FrodoKEM joined the standardization call conducted by theNational Institute of Standards and Technology (NIST),[1]and lived up to the 3rd round of the process. It was then discarded due to low performance reasons. In October, 2022, the Twitter account associated to cryptologistDaniel J. Bernsteinposted security issues in frodokem640.[23]
FrodoKEM,
[
21
]
[
22
]
a scheme based on the learning with errors (LWE) problem. FrodoKEM joined the standardization call conducted by the
National Institute of Standards and Technology (NIST)
,
[
1
]
and lived up to the 3rd round of the process. It was then discarded due to low performance reasons. In October, 2022, the Twitter account associated to cryptologist
Daniel J. Bernstein
posted security issues in frodokem640.
[
23
]
- NewHopeis based on the ring learning with errors (RLWE) problem.[24]
NewHope
is based on the ring learning with errors (RLWE) problem.
[
24
]
- NTRU Prime.[25]
NTRU Prime.
[
25
]
- Peikert's work, which is based on the ring learning with errors (RLWE) problem.[10]
Peikert's work
, which is based on the ring learning with errors (RLWE) problem.
[
10
]
- Saber,[26]which is based on the module learning with rounding (module-LWR) problem.
Saber,
[
26
]
which is based on the module learning with rounding (module-LWR) problem.

### Signing

Signing
[
edit
]
This section lists a selection of lattice-based schemes for the purpose of digital signatures.

This section lists a selection of lattice-based schemes for the purpose of digital signatures.
- CRYSTALS-Dilithium,[27][28]which is built upon module learning with errors (module-LWE) and module short integer solution (module-SIS). Dilithium was selected for standardization by the NIST.[1]According to a message from Ray Perlner, writing on behalf of the NIST PQC team, the NIST module-LWE signing standard is to be based on version 3.1 of the Dilithium specification.
CRYSTALS-Dilithium,
[
27
]
[
28
]
which is built upon module learning with errors (module-LWE) and module short integer solution (module-SIS). Dilithium was selected for standardization by the NIST.
[
1
]
According to a message from Ray Perlner, writing on behalf of the NIST PQC team, the NIST module-LWE signing standard is to be based on version 3.1 of the Dilithium specification.
- Falcon, which is built upon short integer solution (SIS) over NTRU. Falcon was selected for standardization by the NIST.[29][1]
Falcon
, which is built upon short integer solution (SIS) over NTRU. Falcon was selected for standardization by the NIST.
[
29
]
[
1
]
- GGH signature scheme.
GGH signature scheme
.
- Güneysu, Lyubashevsky, and Pöppelmann's work, which is based on ring learning with errors (RLWE).[30]
Güneysu, Lyubashevsky, and Pöppelmann's work, which is based on ring learning with errors (RLWE).
[
30
]
- MITAKA, a variant of Falcon.[31]
MITAKA, a variant of Falcon.
[
31
]
- NTRUSign.
NTRUSign
.
- qTESLA, which is based on ring learning with errors (RLWE). The qTESLA scheme joined the standardization call conducted by theNational Institute of Standards and Technology (NIST).[32][1]
qTESLA, which is based on ring learning with errors (RLWE). The qTESLA scheme joined the standardization call conducted by the
National Institute of Standards and Technology (NIST)
.
[
32
]
[
1
]

#### CRYSTALS-Dilithium

CRYSTALS-Dilithium
[
edit
]
CRYSTALS-Dilithium or simply Dilithium[27][28]is built upon module-LWE and module-SIS. Dilithium was selected by the NIST as the basis for a digital signature standard.[1]According to a message from Ray Perlner, writing on behalf of the NIST PQC team, the NIST module-LWE signing standard is to be based on version 3.1 of the Dilithium specification. NIST's changes on Dilithium 3.1 intend to support additional randomness in signing (hedged signing) and other improvements.[33]

CRYSTALS-Dilithium or simply Dilithium
[
27
]
[
28
]
is built upon module-LWE and module-SIS. Dilithium was selected by the NIST as the basis for a digital signature standard.
[
1
]
According to a message from Ray Perlner, writing on behalf of the NIST PQC team, the NIST module-LWE signing standard is to be based on version 3.1 of the Dilithium specification. NIST's changes on Dilithium 3.1 intend to support additional randomness in signing (hedged signing) and other improvements.
[
33
]
Dilithium was one of the two digital signature schemes initially chosen by the NIST in their post-quantum cryptography process, the other one beingSPHINCS+, which is not based on lattices but on hashes.

Dilithium was one of the two digital signature schemes initially chosen by the NIST in their post-quantum cryptography process, the other one being
SPHINCS+
, which is not based on lattices but on hashes.
In August 2023, NIST published FIPS 204 (Initial Public Draft), and started calling Dilithium "Module-Lattice-Based Digital Signature Algorithm" (ML-DSA).[34]

In August 2023, NIST published FIPS 204 (Initial Public Draft), and started calling Dilithium "Module-Lattice-Based Digital Signature Algorithm" (ML-DSA).
[
34
]
As of October 2023, ML-DSA was being implemented as a part ofLibgcrypt, according to Falko Strenzke.[35]

As of October 2023, ML-DSA was being implemented as a part of
Libgcrypt
, according to Falko Strenzke.
[
35
]
In August 2024,NISTofficially standardized CRYSTALS-Dilithium under the name ML-DSA, establishing it as the primary standard (FIPS 204[36]) for quantum-resistant digital signatures.[37]

In August 2024,
NIST
officially standardized CRYSTALS-Dilithium under the name ML-DSA, establishing it as the primary standard (FIPS 204
[
36
]
) for quantum-resistant digital signatures.
[
37
]

## Security

Security
[
edit
]
Lattice-based cryptographic constructions hold a great promise forpublic-keypost-quantum cryptography.[38]Indeed, the main alternative forms of public-key cryptography are schemes based on the hardness offactoringandrelated problemsand schemes based on the hardness of thediscrete logarithmandrelated problems. However, both factoring and the discrete logarithm problem are known to be solvable inpolynomial time on a quantum computer.[39]Furthermore, algorithms for factorization tend to yield algorithms for discrete logarithm, and conversely. This further motivates the study of constructions based on alternative assumptions, such as the hardness of lattice problems.

Lattice-based cryptographic constructions hold a great promise for
public-key
post-quantum cryptography
.
[
38
]
Indeed, the main alternative forms of public-key cryptography are schemes based on the hardness of
factoring
and
related problems
and schemes based on the hardness of the
discrete logarithm
and
related problems
. However, both factoring and the discrete logarithm problem are known to be solvable in
polynomial time on a quantum computer
.
[
39
]
Furthermore, algorithms for factorization tend to yield algorithms for discrete logarithm, and conversely. This further motivates the study of constructions based on alternative assumptions, such as the hardness of lattice problems.
Many lattice-based cryptographic schemes are known to be secure assuming theworst-casehardness of certain lattice problems.[3][6][7]I.e., if there exists an algorithm that can efficiently break the cryptographic scheme with non-negligible probability, then there exists an efficient algorithm that solves a certain lattice problem on any input. However, for the practical lattice-based constructions (such as schemes based on NTRU and even schemes based on LWE with efficient parameters), meaningful reduction-based guarantees of security are not known.

Many lattice-based cryptographic schemes are known to be secure assuming the
worst-case
hardness of certain lattice problems.
[
3
]
[
6
]
[
7
]
I.e., if there exists an algorithm that can efficiently break the cryptographic scheme with non-negligible probability, then there exists an efficient algorithm that solves a certain lattice problem on any input. However, for the practical lattice-based constructions (such as schemes based on NTRU and even schemes based on LWE with efficient parameters), meaningful reduction-based guarantees of security are not known.
Assessments of the security levels provided by reduction arguments from hard problems—based on recommended parameter sizes, standard estimates of the computational complexity of the hard problems, and detailed examination of the steps in the reductions—are calledconcrete securityand sometimespractice-oriented provable security.[40]Some authors who have investigated concrete security for lattice-based cryptosystems have found that the provable security results for such systems do not provide any meaningful concrete security for practical values of the parameters.[41]

Assessments of the security levels provided by reduction arguments from hard problems—based on recommended parameter sizes, standard estimates of the computational complexity of the hard problems, and detailed examination of the steps in the reductions—are called
concrete security
and sometimes
practice-oriented provable security
.
[
40
]
Some authors who have investigated concrete security for lattice-based cryptosystems have found that the provable security results for such systems do not provide any meaningful concrete security for practical values of the parameters.
[
41
]

## Functionality

Functionality
[
edit
]
For many cryptographic primitives, the only known constructions are based on lattices or closely related objects. These primitives includefully homomorphic encryption,[13]indistinguishability obfuscation,[42]cryptographic multilinear maps, andfunctional encryption.[42]

For many cryptographic primitives, the only known constructions are based on lattices or closely related objects. These primitives include
fully homomorphic encryption
,
[
13
]
indistinguishability obfuscation
,
[
42
]
cryptographic multilinear maps
, and
functional encryption
.
[
42
]

## See also

See also
[
edit
]
- Lattice problems
Lattice problems
- Learning with errors
Learning with errors
- Homomorphic encryption
Homomorphic encryption
- Post-quantum cryptography
Post-quantum cryptography
- Ring learning with errors
Ring learning with errors
- Ring learning with Errors Key Exchange
Ring learning with Errors Key Exchange

## References

References
[
edit
]
- ^abcdefgCSRC, National Institute of Standards and Technology. Post-Quantum Cryptography. 2019. Available from the Internet on <https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/>, accessed in November 2nd, 2022.
^
a
b
c
d
e
f
g
CSRC, National Institute of Standards and Technology. Post-Quantum Cryptography. 2019. Available from the Internet on <
https://csrc.nist.gov/Projects/Post-Quantum-Cryptography/
>, accessed in November 2nd, 2022.
- ^"Module-Lattice-Based Digital Signature Standard"(PDF).NIST.gov. August 2024.
^
"Module-Lattice-Based Digital Signature Standard"
(PDF)
.
NIST.gov
. August 2024.
- ^abAjtai, Miklós (1996). "Generating Hard Instances of Lattice Problems".Proceedings of the Twenty-Eighth Annual ACM Symposium on Theory of Computing. pp.99–108.CiteSeerX10.1.1.40.2489.doi:10.1145/237814.237838.ISBN978-0-89791-785-8.S2CID6864824.
^
a
b
Ajtai, Miklós (1996). "Generating Hard Instances of Lattice Problems".
Proceedings of the Twenty-Eighth Annual ACM Symposium on Theory of Computing
. pp.
99–
108.
CiteSeerX
10.1.1.40.2489
.
doi
:
10.1145/237814.237838
.
ISBN
978-0-89791-785-8
.
S2CID
6864824
.
- ^Public-Key Cryptosystem with Worst-Case/Average-Case Equivalence.
^
Public-Key Cryptosystem with Worst-Case/Average-Case Equivalence
.
- ^Hoffstein, Jeffrey; Pipher, Jill; Silverman, Joseph H. (1998). "NTRU: A ring-based public key cryptosystem".Algorithmic Number Theory. Lecture Notes in Computer Science. Vol. 1423. pp.267–288.CiteSeerX10.1.1.25.8422.doi:10.1007/bfb0054868.ISBN978-3-540-64657-0.
^
Hoffstein, Jeffrey; Pipher, Jill; Silverman, Joseph H. (1998). "NTRU: A ring-based public key cryptosystem".
Algorithmic Number Theory
. Lecture Notes in Computer Science. Vol. 1423. pp.
267–
288.
CiteSeerX
10.1.1.25.8422
.
doi
:
10.1007/bfb0054868
.
ISBN
978-3-540-64657-0
.
- ^abRegev, Oded (2005-01-01). "On lattices, learning with errors, random linear codes, and cryptography".Proceedings of the thirty-seventh annual ACM symposium on Theory of computing – STOC '05. ACM. pp.84–93.CiteSeerX10.1.1.110.4776.doi:10.1145/1060590.1060603.ISBN978-1581139600.S2CID53223958.
^
a
b
Regev, Oded (2005-01-01). "On lattices, learning with errors, random linear codes, and cryptography".
Proceedings of the thirty-seventh annual ACM symposium on Theory of computing – STOC '05
. ACM. pp.
84–
93.
CiteSeerX
10.1.1.110.4776
.
doi
:
10.1145/1060590.1060603
.
ISBN
978-1581139600
.
S2CID
53223958
.
- ^abPeikert, Chris (2009-01-01). "Public-key cryptosystems from the worst-case shortest vector problem".Proceedings of the 41st annual ACM symposium on Symposium on theory of computing – STOC '09. ACM. pp.333–342.CiteSeerX10.1.1.168.270.doi:10.1145/1536414.1536461.ISBN9781605585062.S2CID1864880.
^
a
b
Peikert, Chris (2009-01-01). "Public-key cryptosystems from the worst-case shortest vector problem".
Proceedings of the 41st annual ACM symposium on Symposium on theory of computing – STOC '09
. ACM. pp.
333–
342.
CiteSeerX
10.1.1.168.270
.
doi
:
10.1145/1536414.1536461
.
ISBN
9781605585062
.
S2CID
1864880
.
- ^Brakerski, Zvika; Langlois, Adeline; Peikert, Chris; Regev, Oded; Stehlé, Damien (2013-01-01). "Classical hardness of learning with errors".Proceedings of the 45th annual ACM symposium on Symposium on theory of computing – STOC '13. ACM. pp.575–584.arXiv:1306.0281.doi:10.1145/2488608.2488680.ISBN9781450320290.S2CID6005009.
^
Brakerski, Zvika; Langlois, Adeline; Peikert, Chris; Regev, Oded; Stehlé, Damien (2013-01-01). "Classical hardness of learning with errors".
Proceedings of the 45th annual ACM symposium on Symposium on theory of computing – STOC '13
. ACM. pp.
575–
584.
arXiv
:
1306.0281
.
doi
:
10.1145/2488608.2488680
.
ISBN
9781450320290
.
S2CID
6005009
.
- ^Lyubashevsky, Vadim; Peikert, Chris; Regev, Oded (2010-05-30). "On Ideal Lattices and Learning with Errors over Rings".Advances in Cryptology – EUROCRYPT 2010. Lecture Notes in Computer Science. Vol. 6110. pp.1–23.CiteSeerX10.1.1.352.8218.doi:10.1007/978-3-642-13190-5_1.ISBN978-3-642-13189-9.
^
Lyubashevsky, Vadim; Peikert, Chris; Regev, Oded (2010-05-30). "On Ideal Lattices and Learning with Errors over Rings".
Advances in Cryptology – EUROCRYPT 2010
. Lecture Notes in Computer Science. Vol. 6110. pp.
1–
23.
CiteSeerX
10.1.1.352.8218
.
doi
:
10.1007/978-3-642-13190-5_1
.
ISBN
978-3-642-13189-9
.
- ^abPeikert, Chris (2014-07-16)."Lattice cryptography for the Internet"(PDF).IACR. Retrieved2017-01-11.
^
a
b
Peikert, Chris (2014-07-16).
"Lattice cryptography for the Internet"
(PDF)
.
IACR
. Retrieved
2017-01-11
.
- ^Alkim, Erdem; Ducas, Léo; Pöppelmann, Thomas; Schwabe, Peter (2015-01-01)."Post-quantum key exchange – a new hope".Cryptology ePrint Archive.
^
Alkim, Erdem; Ducas, Léo; Pöppelmann, Thomas; Schwabe, Peter (2015-01-01).
"Post-quantum key exchange – a new hope"
.
Cryptology ePrint Archive
.
- ^Bos, Joppe; Costello, Craig; Ducas, Léo; Mironov, Ilya; Naehrig, Michael; Nikolaenko, Valeria; Raghunathan, Ananth; Stebila, Douglas (2016-01-01)."Frodo: Take off the ring! Practical, Quantum-Secure Key Exchange from LWE".Cryptology ePrint Archive.
^
Bos, Joppe; Costello, Craig; Ducas, Léo; Mironov, Ilya; Naehrig, Michael; Nikolaenko, Valeria; Raghunathan, Ananth; Stebila, Douglas (2016-01-01).
"Frodo: Take off the ring! Practical, Quantum-Secure Key Exchange from LWE"
.
Cryptology ePrint Archive
.
- ^abcGentry, Craig (2009-01-01).A Fully Homomorphic Encryption Scheme(Thesis). Stanford, CA, USA: Stanford University.
^
a
b
c
Gentry, Craig (2009-01-01).
A Fully Homomorphic Encryption Scheme
(Thesis). Stanford, CA, USA: Stanford University.
- ^NGUYEN, Phon. Cryptanalysis of the Goldreich-Goldwasser-Halevi Cryptosystem from crypto ’97. InCrypto ’99: Proceedings of the 19th Annual International Cryptology Conference on Advances in Cryptology, pages 288–304, London, UK, 1999. Springer-Verlag.
^
NGUYEN, Phon. Cryptanalysis of the Goldreich-Goldwasser-Halevi Cryptosystem from crypto ’97. In
Crypto ’99: Proceedings of the 19th Annual International Cryptology Conference on Advances in Cryptology
, pages 288–304, London, UK, 1999. Springer-Verlag.
- ^Brakerski, Zvika; Vaikuntanathan, Vinod (2011)."Efficient Fully Homomorphic Encryption from (Standard) LWE".Cryptology ePrint Archive.
^
Brakerski, Zvika; Vaikuntanathan, Vinod (2011).
"Efficient Fully Homomorphic Encryption from (Standard) LWE"
.
Cryptology ePrint Archive
.
- ^Brakerski, Zvika; Vaikuntanathan, Vinod (2013)."Lattice-Based FHE as Secure as PKE".Cryptology ePrint Archive.
^
Brakerski, Zvika; Vaikuntanathan, Vinod (2013).
"Lattice-Based FHE as Secure as PKE"
.
Cryptology ePrint Archive
.
- ^"LASH: A Lattice Based Hash Function". Archived fromthe originalon October 16, 2008. Retrieved2008-07-31.
^
"LASH: A Lattice Based Hash Function"
. Archived from
the original
on October 16, 2008
. Retrieved
2008-07-31
.
- ^Contini, Scott; Matusiewicz, Krystian; Pieprzyk, Josef; Steinfeld, Ron; Guo, Jian; Ling, San; Wang, Huaxiong (2008)."Cryptanalysis of LASH"(PDF).Fast Software Encryption. Lecture Notes in Computer Science. Vol. 5086. pp.207–223.doi:10.1007/978-3-540-71039-4_13.ISBN978-3-540-71038-7.S2CID6207514.
^
Contini, Scott; Matusiewicz, Krystian; Pieprzyk, Josef; Steinfeld, Ron; Guo, Jian; Ling, San; Wang, Huaxiong (2008).
"Cryptanalysis of LASH"
(PDF)
.
Fast Software Encryption
. Lecture Notes in Computer Science. Vol. 5086. pp.
207–
223.
doi
:
10.1007/978-3-540-71039-4_13
.
ISBN
978-3-540-71038-7
.
S2CID
6207514
.
- ^AVANZI, R. et al. CRYSTALS-KYBER Algorithm Specifications And Supporting Documentation. CRYSTALS Team, 2021. Available from the Internet on <https:
//www.pq-crystals.org/>, accessed on November 4th, 2022.
^
AVANZI, R. et al. CRYSTALS-KYBER Algorithm Specifications And Supporting Documentation. CRYSTALS Team, 2021. Available from the Internet on <https:
//www.pq-crystals.org/>, accessed on November 4th, 2022.
- ^Raimondo, Gina M., and Locascio, Laurie E., FIPS 203 (Draft) Federal Information Processing Standards Publication – Module-Lattice-based Key-Encapsulation Mechanism Standard. August 24, 2023. Information Technology Laboratory, National Institute of Standards and Technology. Gaithersburg, MD, United States of America.doi:10.6028/NIST.FIPS.203.ipd. Available from the Internet on <https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.ipd.pdf>, accessed in October 30th, 2023.
^
Raimondo, Gina M., and Locascio, Laurie E., FIPS 203 (Draft) Federal Information Processing Standards Publication – Module-Lattice-based Key-Encapsulation Mechanism Standard. August 24, 2023. Information Technology Laboratory, National Institute of Standards and Technology. Gaithersburg, MD, United States of America.
doi
:
10.6028/NIST.FIPS.203.ipd
. Available from the Internet on <
https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.ipd.pdf
>, accessed in October 30th, 2023.
- ^FrodoKEM team. FrodoKEM. 2022. Available from the Internet on <https://frodokem.org/>, accessed on November 2nd, 2022.
^
FrodoKEM team. FrodoKEM. 2022. Available from the Internet on <
https://frodokem.org/
>, accessed on November 2nd, 2022.
- ^ALKIM, E. et al. FrodoKEM learning with errors key encapsulation algorithm specifications and supporting documentation. 2020. Available from the Internet on <https://frodokem.org/files/FrodoKEM-specification-20200930.pdf>, accessed in November 1st, 2022
^
ALKIM, E. et al. FrodoKEM learning with errors key encapsulation algorithm specifications and supporting documentation. 2020. Available from the Internet on <
https://frodokem.org/files/FrodoKEM-specification-20200930.pdf
>, accessed in November 1st, 2022
- ^Bernstein, Daniel J. FrodoKEM documentation claims that "the FrodoKEM parameter sets comfortably match their target security levels with a large margin". Warning: That's not true. Send 2^40 ciphertexts to a frodokem640 public key; one of them will be decrypted by a large-scale attack feasible today. 2022. Available from the Internet on <https://twitter.com/hashbreaker/status/1587184970258255872>, accessed in November 2nd, 2022.
^
Bernstein, Daniel J. FrodoKEM documentation claims that "the FrodoKEM parameter sets comfortably match their target security levels with a large margin". Warning: That's not true. Send 2^40 ciphertexts to a frodokem640 public key; one of them will be decrypted by a large-scale attack feasible today. 2022. Available from the Internet on <
https://twitter.com/hashbreaker/status/1587184970258255872
>, accessed in November 2nd, 2022.
- ^SCHWABE, Peter et al. NewHope's Web site. 2022. Available from the Internet on <https://newhopecrypto.org/>, accessed in December 6th, 2022.
^
SCHWABE, Peter et al. NewHope's Web site. 2022. Available from the Internet on <
https://newhopecrypto.org/
>, accessed in December 6th, 2022.
- ^Bernstein, Daniel J. et al., NTRU Prime: round 3. 2020. Available from the Internet on <https://ntruprime.cr.yp.to/>, accessed in November 8th, 2022.
^
Bernstein, Daniel J. et al., NTRU Prime: round 3. 2020. Available from the Internet on <
https://ntruprime.cr.yp.to/
>, accessed in November 8th, 2022.
- ^D'ANVERS, Jan-Pieter, KARMAKAR, Angshuman, ROY, Sujoy Sinha, and VERCAUTEREN, Frederik. Saber: Module-LWR based key exchange, CPA-secure encryption and CCA-secure KEM. 2018. Available from Internet on <https://eprint.iacr.org/2018/230>, accessed in November 5th, 2022.
^
D'ANVERS, Jan-Pieter, KARMAKAR, Angshuman, ROY, Sujoy Sinha, and VERCAUTEREN, Frederik. Saber: Module-LWR based key exchange, CPA-secure encryption and CCA-secure KEM. 2018. Available from Internet on <
https://eprint.iacr.org/2018/230
>, accessed in November 5th, 2022.
- ^abBAI, S. et al. CRYSTALS-Dilithium Algorithm Specifications and Supporting Documentation (Version 3.1). CRYSTALS Team, 2021. Available from the Internet on <https://www.pq-crystals.org/>, accessed in November 2nd, 2021.
^
a
b
BAI, S. et al. CRYSTALS-Dilithium Algorithm Specifications and Supporting Documentation (Version 3.1). CRYSTALS Team, 2021. Available from the Internet on <
https://www.pq-crystals.org/
>, accessed in November 2nd, 2021.
- ^abSEILER, Gregor et al. pq-crystals/dilithium (Dilithium at GitHub), 2022. Available from the Internet on <https://github.com/pq-crystals/dilithium>, accessed in December 29th, 2022.
^
a
b
SEILER, Gregor et al. pq-crystals/dilithium (Dilithium at GitHub), 2022. Available from the Internet on <
https://github.com/pq-crystals/dilithium
>, accessed in December 29th, 2022.
- ^FOUQUE, Pierre-Alain et al. Falcon: Fast-Fourier Lattice-based Compact Signatures over NTRU. 2020. Available from the Internet on <https://falcon-sign.info/>, accessed in November 8th, 2020.
^
FOUQUE, Pierre-Alain et al. Falcon: Fast-Fourier Lattice-based Compact Signatures over NTRU. 2020. Available from the Internet on <
https://falcon-sign.info/
>, accessed in November 8th, 2020.
- ^Güneysu, Tim; Lyubashevsky, Vadim; Pöppelmann, Thomas (2012)."Practical Lattice-Based Cryptography: A Signature Scheme for Embedded Systems"(PDF).Cryptographic Hardware and Embedded Systems – CHES 2012. Lecture Notes in Computer Science. Vol. 7428. IACR. pp.530–547.doi:10.1007/978-3-642-33027-8_31.ISBN978-3-642-33026-1. Retrieved2017-01-11.
^
Güneysu, Tim; Lyubashevsky, Vadim; Pöppelmann, Thomas (2012).
"Practical Lattice-Based Cryptography: A Signature Scheme for Embedded Systems"
(PDF)
.
Cryptographic Hardware and Embedded Systems – CHES 2012
. Lecture Notes in Computer Science. Vol. 7428. IACR. pp.
530–
547.
doi
:
10.1007/978-3-642-33027-8_31
.
ISBN
978-3-642-33026-1
. Retrieved
2017-01-11
.
- ^ESPITAU, Thomas et al. MITAKA: A Simpler, Parallelizable, Maskable Variant of Falcon. 2021.
^
ESPITAU, Thomas et al. MITAKA: A Simpler, Parallelizable, Maskable Variant of Falcon. 2021.
- ^ALKIM, E. et al. The Lattice-Based Digital Signature Scheme qTESLA. IACR, 2019. Cryptology ePrint Archive, Report 2019/085. Available from Internet on <https://eprint.iacr.org/2019/085>, accessed in NOVEMBER 1st, 2022.
^
ALKIM, E. et al. The Lattice-Based Digital Signature Scheme qTESLA. IACR, 2019. Cryptology ePrint Archive, Report 2019/085. Available from Internet on <
https://eprint.iacr.org/2019/085
>, accessed in NOVEMBER 1st, 2022.
- ^Perlner, Ray A.. Planned changes to the Dilithium spec. April 20th, 2023. Google Groups. Available from the Internet on <https://groups.google.com/a/list.nist.gov/g/pqc-forum/c/3pBJsYjfRw4/m/GjJ2icQkAQAJ>, accessed in June 14th, 2023.
^
Perlner, Ray A.. Planned changes to the Dilithium spec. April 20th, 2023. Google Groups. Available from the Internet on <
https://groups.google.com/a/list.nist.gov/g/pqc-forum/c/3pBJsYjfRw4/m/GjJ2icQkAQAJ
>, accessed in June 14th, 2023.
- ^Raimondo, Gina M., and Locascio, Laurie E., FIPS 204 (Draft) Federal Information Processing Standards Publication – Module-Lattice-Based Digital Signature Standard. August 24, 2023. Information Technology Laboratory, National Institute of Standards and Technology. Gaithersburg, MD, United States of America.doi:10.6028/NIST.FIPS.204.ipd. Available from the Internet on <https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.ipd.pdf>, accessed in September 2nd, 2023.
^
Raimondo, Gina M., and Locascio, Laurie E., FIPS 204 (Draft) Federal Information Processing Standards Publication – Module-Lattice-Based Digital Signature Standard. August 24, 2023. Information Technology Laboratory, National Institute of Standards and Technology. Gaithersburg, MD, United States of America.
doi
:
10.6028/NIST.FIPS.204.ipd
. Available from the Internet on <
https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.ipd.pdf
>, accessed in September 2nd, 2023.
- ^Gcrypt-devel mailing list. Dilithium Implementation in Libgcrypt. October 24th, 2023. Available from the Internet on <https://lists.gnupg.org/pipermail/gcrypt-devel/2023-October/005572.html>, accessed on October 24th, 2023.
^
Gcrypt-devel mailing list. Dilithium Implementation in Libgcrypt. October 24th, 2023. Available from the Internet on <
https://lists.gnupg.org/pipermail/gcrypt-devel/2023-October/005572.html
>, accessed on October 24th, 2023.
- ^Technology, National Institute of Standards and (2024-08-13).Module-Lattice-Based Digital Signature Standard(Report). U.S. Department of Commerce.
^
Technology, National Institute of Standards and (2024-08-13).
Module-Lattice-Based Digital Signature Standard
(Report). U.S. Department of Commerce.
- ^"NIST Releases First 3 Finalized Post-Quantum Encryption Standards".NIST. 2024-08-13.
^
"NIST Releases First 3 Finalized Post-Quantum Encryption Standards"
.
NIST
. 2024-08-13.
- ^Micciancio, Daniele; Regev, Oded (2008-07-22)."Lattice-based cryptography"(PDF).Nyu.edu. Retrieved2017-01-11.
^
Micciancio, Daniele; Regev, Oded (2008-07-22).
"Lattice-based cryptography"
(PDF)
.
Nyu.edu
. Retrieved
2017-01-11
.
- ^Shor, Peter W. (1997-10-01). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".SIAM Journal on Computing.26(5):1484–1509.arXiv:quant-ph/9508027.doi:10.1137/S0097539795293172.ISSN0097-5397.S2CID2337707.
^
Shor, Peter W. (1997-10-01). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".
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
doi
:
10.1137/S0097539795293172
.
ISSN
0097-5397
.
S2CID
2337707
.
- ^Bellare, Mihir (1998),Practice-Oriented Provable-Security, Lecture Notes in Computer Science, vol. 1396, Springer-Verlag, pp.221–231,doi:10.1007/BFb0030423
^
Bellare, Mihir (1998),
Practice-Oriented Provable-Security
, Lecture Notes in Computer Science, vol. 1396, Springer-Verlag, pp.
221–
231,
doi
:
10.1007/BFb0030423
- ^Gärtner, Joel (2023),Concrete Security from Worst-Case to Average-Case Lattice Reductions, Lecture Notes in Computer Science, vol. 14064, Springer-Verlag, pp.344–369,ISBN978-3-031-37678-8
^
Gärtner, Joel (2023),
Concrete Security from Worst-Case to Average-Case Lattice Reductions
, Lecture Notes in Computer Science, vol. 14064, Springer-Verlag, pp.
344–
369,
ISBN
978-3-031-37678-8
- ^abGarg, Sanjam; Gentry, Craig; Halevi, Shai; Raykova, Mariana; Sahai, Amit; Waters, Brent (2013-01-01)."Candidate Indistinguishability Obfuscation and Functional Encryption for all circuits".Cryptology ePrint Archive.CiteSeerX10.1.1.400.6501.
^
a
b
Garg, Sanjam; Gentry, Craig; Halevi, Shai; Raykova, Mariana; Sahai, Amit; Waters, Brent (2013-01-01).
"Candidate Indistinguishability Obfuscation and Functional Encryption for all circuits"
.
Cryptology ePrint Archive
.
CiteSeerX
10.1.1.400.6501
.

## Further reading

Further reading
[
edit
]
- Goldreich, Oded; Goldwasser, Shafi; Halevi, Shai (1997). "Public-key cryptosystems from lattice reduction problems".Crypto ’97: Proceedings of the 17th Annual International Cryptology Conference on Advances in Cryptology. London, UK: Springer-Verlag. pp.112–131.doi:10.1007/BFb0052231.ISBN978-3-540-63384-6.
Goldreich, Oded; Goldwasser, Shafi; Halevi, Shai (1997). "Public-key cryptosystems from lattice reduction problems".
Crypto ’97: Proceedings of the 17th Annual International Cryptology Conference on Advances in Cryptology
. London, UK: Springer-Verlag. pp.
112–
131.
doi
:
10.1007/BFb0052231
.
ISBN
978-3-540-63384-6
.
- Regev, Oded (2006). "Lattice-based cryptography".Advances in cryptology (CRYPTO). Springer-Verlag. pp.131–141.doi:10.1007/11818175_8.ISBN978-3-540-37432-9.
Regev, Oded (2006). "Lattice-based cryptography".
Advances in cryptology (CRYPTO)
. Springer-Verlag. pp.
131–
141.
doi
:
10.1007/11818175_8
.
ISBN
978-3-540-37432-9
.

## External links

External links
[
edit
]
- Dilithium Demo in Excel- Example implementation and demonstration in Excel (without macros) by Tim Wambach.
Dilithium Demo in Excel
- Example implementation and demonstration in Excel (without macros) by Tim Wambach.

<!-- table omitted -->

- v
v
- t
t
- e
e
Public-key cryptography
Algorithms

<!-- table omitted -->

Integer factorization
- Benaloh
Benaloh
- Blum–Goldwasser
Blum–Goldwasser
- Cayley–Purser
Cayley–Purser
- Damgård–Jurik
Damgård–Jurik
- GMR
GMR
- Goldwasser–Micali
Goldwasser–Micali
- Naccache–Stern
Naccache–Stern
- Paillier
Paillier
- Rabin
Rabin
- RSA
RSA
- Okamoto–Uchiyama
Okamoto–Uchiyama
- Schmidt–Samoa
Schmidt–Samoa
Discrete logarithm
- BLS
BLS
- Cramer–Shoup
Cramer–Shoup
- DH
DH
- DSA
DSA
- ECDHX25519X448
ECDH
- X25519
X25519
- X448
X448
- ECDSA
ECDSA
- EdDSAEd25519Ed448
EdDSA
- Ed25519
Ed25519
- Ed448
Ed448
- ECMQV
ECMQV
- EKE
EKE
- ElGamalsignature scheme
ElGamal
- signature scheme
signature scheme
- MQV
MQV
- Schnorr
Schnorr
- SPEKE
SPEKE
- SRP
SRP
- STS
STS
Lattice/SVP/CVP
/
LWE
/
SIS
- BLISS
BLISS
- Kyber
Kyber
- NewHope
NewHope
- NTRUEncrypt
NTRUEncrypt
- NTRUSign
NTRUSign
- RLWE-KEX
RLWE-KEX
- RLWE-SIG
RLWE-SIG
- Falcon
Falcon
Others
- AE
AE
- CEILIDH
CEILIDH
- EPOC
EPOC
- HFE
HFE
- IES
IES
- Lamport
Lamport
- McEliece
McEliece
- Merkle–Hellman
Merkle–Hellman
- Naccache–Stern knapsack cryptosystem
Naccache–Stern knapsack cryptosystem
- Three-pass protocol
Three-pass protocol
- XTR
XTR
- SQIsign
SQIsign
- SPHINCS+
SPHINCS
+
Theory
- Discrete logarithm cryptography
Discrete logarithm cryptography
- Elliptic-curve cryptography
Elliptic-curve cryptography
- Hash-based cryptography
Hash-based cryptography
- Non-commutative cryptography
Non-commutative cryptography
- RSA problem
RSA problem
- Trapdoor function
Trapdoor function
- Tropical cryptography
Tropical cryptography
Standardization
- CRYPTREC
CRYPTREC
- IEEE P1363
IEEE P1363
- NESSIE
NESSIE
- NSA Suite B
NSA Suite B
- CNSA
CNSA
- Post-Quantum Cryptography
Post-Quantum Cryptography
Topics
- Digital signature
Digital signature
- OAEP
OAEP
- Fingerprint
Fingerprint
- PKI
PKI
- Web of trust
Web of trust
- Key size
Key size
- Identity-based cryptography
Identity-based cryptography
- Post-quantum cryptography
Post-quantum cryptography
- OpenPGP card
OpenPGP card

<!-- table omitted -->


<!-- table omitted -->

- v
v
- t
t
- e
e
Cryptography
General
- History of cryptography
History of cryptography
- Outline of cryptography
Outline of cryptography
- Classical cipher
Classical cipher
- Cryptographic protocolAuthentication protocol
Cryptographic protocol
- Authentication protocol
Authentication protocol
- Cryptographic primitive
Cryptographic primitive
- Cryptanalysis
Cryptanalysis
- Cryptocurrency
Cryptocurrency
- Cryptosystem
Cryptosystem
- Cryptographic nonce
Cryptographic nonce
- Cryptovirology
Cryptovirology
- Hash functionCryptographic hash functionKey derivation functionSecure Hash Algorithms
Hash function
- Cryptographic hash function
Cryptographic hash function
- Key derivation function
Key derivation function
- Secure Hash Algorithms
Secure Hash Algorithms
- Digital signature
Digital signature
- Kleptography
Kleptography
- Key (cryptography)
Key (cryptography)
- Key exchange
Key exchange
- Key generator
Key generator
- Key schedule
Key schedule
- Key stretching
Key stretching
- Keygen
Keygen
- Machines
Machines
- Ransomware
Ransomware
- Random number generationCryptographically secure pseudorandom number generator(CSPRNG)
Random number generation
- Cryptographically secure pseudorandom number generator(CSPRNG)
Cryptographically secure pseudorandom number generator
(CSPRNG)
- Pseudorandom noise(PRN)
Pseudorandom noise
(PRN)
- Secure channel
Secure channel
- Insecure channel
Insecure channel
- Subliminal channel
Subliminal channel
- Encryption
Encryption
- Decryption
Decryption
- End-to-end encryption
End-to-end encryption
- Harvest now, decrypt later
Harvest now, decrypt later
- Information-theoretic security
Information-theoretic security
- Plaintext
Plaintext
- Codetext
Codetext
- Ciphertext
Ciphertext
- Shared secret
Shared secret
- Trapdoor function
Trapdoor function
- Trusted timestamping
Trusted timestamping
- Key-based routing
Key-based routing
- Onion routing
Onion routing
- Garlic routing
Garlic routing
- Kademlia
Kademlia
- Mix network
Mix network
Mathematics
- Cryptographic hash function
Cryptographic hash function
- Block cipher
Block cipher
- Stream cipher
Stream cipher
- Symmetric-key algorithm
Symmetric-key algorithm
- Authenticated encryption
Authenticated encryption
- Public-key cryptography
Public-key cryptography
- Quantum key distribution
Quantum key distribution
- Quantum cryptography
Quantum cryptography
- Post-quantum cryptography
Post-quantum cryptography
- Message authentication code
Message authentication code
- Random numbers
Random numbers
- Steganography
Steganography
- Category
Category
NewPP limit report
Parsed by mw‐web.codfw.main‐7c6c8bdf8c‐2btng
Cached time: 20260611175902
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, show‐toc]
CPU time usage: 0.417 seconds
Real time usage: 0.508 seconds
Preprocessor visited node count: 1686/1000000
Revision size: 24511/2097152 bytes
Post‐expand include size: 88266/2097152 bytes
Template argument size: 636/2097152 bytes
Highest expansion depth: 8/100
Expensive parser function count: 1/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 130647/5000000 bytes
Lua time usage: 0.254/10.000 seconds
Lua memory usage: 5522344/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  385.611      1 -total
 57.83%  223.000      1 Template:Reflist
 22.20%   85.611      3 Template:Cite_web
 17.76%   68.491      1 Template:Cryptography_public-key
 14.24%   54.893     10 Template:Cite_book
 12.56%   48.447      1 Template:Short_description
 10.00%   38.565      8 Template:Cite_journal
  8.02%   30.931      2 Template:Pagetype
  5.29%   20.386      3 Template:Navbox
  3.36%   12.944      1 Template:Cryptography_navbox
Render ID 3a82b89c-65bf-11f1-b1f5-d36d6b1753fa
Saved in parser cache with key enwiki:pcache:18657553:|#|:idhash:canonical and timestamp 20260611175902 and revision id 1322231844. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Lattice-based_cryptography&oldid=1322231844
"
Categories
:
- Lattice-based cryptography
Lattice-based cryptography
- Post-quantum cryptography
Post-quantum cryptography
Hidden categories:
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata