<!-- source: https://en.wikipedia.org/wiki/Quantum_cryptography -->
# Quantum cryptography

> Source: https://en.wikipedia.org/wiki/Quantum_cryptography
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Cryptography based on quantum mechanical phenomena
Compare
post-quantum cryptography
, which is any cryptography (nonquantum or quantum) that resists cryptanalysis that uses quantum computing.
Quantum cryptographyis the science of exploitingquantum mechanicalproperties such as quantum entanglement, measurement disturbance, no-cloning theorem, and the principle ofsuperpositionto perform variouscryptographictasks.[1][2][3]Historically defined as the practice of encoding messages, a concept since referred to asencryption, quantum cryptography plays a crucial role in the secure processing, storage, and transmission of information across various domains.

Quantum cryptography
is the science of exploiting
quantum mechanical
properties such as quantum entanglement, measurement disturbance, no-cloning theorem, and the principle of
superposition
to perform various
cryptographic
tasks.
[
1
]
[
2
]
[
3
]
Historically defined as the practice of encoding messages, a concept since referred to as
encryption
, quantum cryptography plays a crucial role in the secure processing, storage, and transmission of information across various domains.
One aspect of quantum cryptography isquantum key distribution(QKD), which offers aninformation-theoretically securesolution to thekey exchangeproblem. The advantage of quantum cryptography lies in the fact that it allows the completion of various cryptographic tasks that are proven or conjectured to be impossible using only classical (i.e. non-quantum) communication. Furthermore, quantum cryptography affords the authentication of messages, which allows the legitimates parties to prove that the messages were not wiretapped during transmission.[4]For example, in a cryptographic set-up, it isimpossible to copywith perfect fidelity, the data encoded in aquantum state.[5][pageneeded]If one attempts to read the encoded data, the quantum state will be changed due towave function collapse(no-cloning theorem). This could be used to detect eavesdropping in QKD schemes, or in quantum communication links and networks. These advantages have significantly influenced the evolution of quantum cryptography, making it practical in the digital age, where devices are increasingly interconnected and cyberattacks have become more sophisticated; as such, quantum cryptography is a critical component in the advancement of a quantum internet, as it establishes robust mechanisms to ensure the long-term privacy and integrity of digital communications and systems.[6]

One aspect of quantum cryptography is
quantum key distribution
(QKD), which offers an
information-theoretically secure
solution to the
key exchange
problem. The advantage of quantum cryptography lies in the fact that it allows the completion of various cryptographic tasks that are proven or conjectured to be impossible using only classical (i.e. non-quantum) communication. Furthermore, quantum cryptography affords the authentication of messages, which allows the legitimates parties to prove that the messages were not wiretapped during transmission.
[
4
]
For example, in a cryptographic set-up, it is
impossible to copy
with perfect fidelity, the data encoded in a
quantum state
.
[
5
]
[
page
needed
]
If one attempts to read the encoded data, the quantum state will be changed due to
wave function collapse
(
no-cloning theorem
). This could be used to detect eavesdropping in QKD schemes, or in quantum communication links and networks. These advantages have significantly influenced the evolution of quantum cryptography, making it practical in the digital age, where devices are increasingly interconnected and cyberattacks have become more sophisticated; as such, quantum cryptography is a critical component in the advancement of a quantum internet, as it establishes robust mechanisms to ensure the long-term privacy and integrity of digital communications and systems.
[
6
]

## History

History
[
edit
]
The polarized light is transmitted across an insecure
quantum channel
and detected by Bob while Eve attempts to eavesdrop on the communication.
In the early 1970s,Stephen Wiesner, then at Columbia University in New York, introduced the concept of quantumconjugate coding. His seminal paper titled "Conjugate Coding" was rejected by theIEEE Information Theory Societybut was eventually published in 1983 inSIGACT News.[7]In this paper he showed how to store or transmit two messages by encoding them in two "conjugateobservables", such as linear and circularpolarizationofphotons,[8]so that either, but not both, properties may be received and decoded. It was not untilCharles H. Bennett, of the IBM'sThomas J. Watson Research Center, andGilles Brassardmet in 1979 at the 20th IEEE Symposium on the Foundations of Computer Science, held in Puerto Rico, that they discovered how to incorporate Wiesner's findings. "The main breakthrough came when we realized that photons were never meant to store information, but rather to transmit it."[7]In 1984, building upon this work, Bennett and Brassard proposed a method forsecure communication, which is now calledBB84, the first Quantum Key Distribution system.[9][10]Independently, in 1991Artur Ekertproposed to use Bell's inequalities to achieve secure key distribution.[11]Ekert's protocol for the key distribution, as it was subsequently shown byDominic MayersandAndrew Yao, offers device-independent quantum key distribution.

In the early 1970s,
Stephen Wiesner
, then at Columbia University in New York, introduced the concept of quantum
conjugate coding
. His seminal paper titled "Conjugate Coding" was rejected by the
IEEE Information Theory Society
but was eventually published in 1983 in
SIGACT News
.
[
7
]
In this paper he showed how to store or transmit two messages by encoding them in two "conjugate
observables
", such as linear and circular
polarization
of
photons
,
[
8
]
so that either, but not both, properties may be received and decoded. It was not until
Charles H. Bennett
, of the IBM's
Thomas J. Watson Research Center
, and
Gilles Brassard
met in 1979 at the 20th IEEE Symposium on the Foundations of Computer Science, held in Puerto Rico, that they discovered how to incorporate Wiesner's findings. "The main breakthrough came when we realized that photons were never meant to store information, but rather to transmit it."
[
7
]
In 1984, building upon this work, Bennett and Brassard proposed a method for
secure communication
, which is now called
BB84
, the first Quantum Key Distribution system.
[
9
]
[
10
]
Independently, in 1991
Artur Ekert
proposed to use Bell's inequalities to achieve secure key distribution.
[
11
]
Ekert's protocol for the key distribution, as it was subsequently shown by
Dominic Mayers
and
Andrew Yao
, offers device-independent quantum key distribution.
Companies that manufacture quantum cryptography systems includeMagiQ Technologies, Inc.(Boston),ID Quantique(Geneva),QuintessenceLabs(Canberra, Australia),Toshiba(Tokyo),QNu Labs(India) and SeQureNet (Paris).

Companies that manufacture quantum cryptography systems include
MagiQ Technologies, Inc.
(Boston),
ID Quantique
(Geneva),
QuintessenceLabs
(Canberra, Australia),
Toshiba
(Tokyo),
QNu Labs
(India) and SeQureNet (Paris).

## Advantages

Advantages
[
edit
]
Cryptography is the strongest link in the chain ofdata security.[12]However, interested parties cannot assume that cryptographic keys will remain secure indefinitely.[13]Quantum cryptography[2]has the potential to encrypt data for longer periods than classical cryptography.[13]Using classical cryptography, scientists cannot guarantee encryption beyond approximately 30 years, but some stakeholders could use longer periods of protection.[13]Take, for example, the healthcare industry. As of 2017, 85.9% of office-based physicians are using electronic medical record systems to store and transmit patient data.[14]Under the Health Insurance Portability and Accountability Act, medical records must be kept secret.[15]Quantum key distribution can protect electronic records for periods of up to 100 years.[13]Also, quantum cryptography has useful applications for governments and militaries as, historically, governments have kept military data secret for periods of over 60 years.[13]There also has been proof that quantum key distribution can travel through a noisy channel over a long distance and be secure. It can be reduced from a noisy quantum scheme to a classical noiseless scheme. This can be solved with classical probability theory.[16]This process of having consistent protection over anoisy channelcan be possible through the implementation of quantum repeaters. Quantum repeaters have the ability to resolve quantum communication errors in an efficient way. Quantum repeaters, which are quantum computers, can be stationed as segments over the noisy channel to ensure the security of communication. Quantum repeaters do this by purifying the segments of the channel before connecting them creating a secure line of communication. Sub-par quantum repeaters can provide an efficient amount of security through the noisy channel over a long distance.[16]

Cryptography is the strongest link in the chain of
data security
.
[
12
]
However, interested parties cannot assume that cryptographic keys will remain secure indefinitely.
[
13
]
Quantum cryptography
[
2
]
has the potential to encrypt data for longer periods than classical cryptography.
[
13
]
Using classical cryptography, scientists cannot guarantee encryption beyond approximately 30 years, but some stakeholders could use longer periods of protection.
[
13
]
Take, for example, the healthcare industry. As of 2017, 85.9% of office-based physicians are using electronic medical record systems to store and transmit patient data.
[
14
]
Under the Health Insurance Portability and Accountability Act, medical records must be kept secret.
[
15
]
Quantum key distribution can protect electronic records for periods of up to 100 years.
[
13
]
Also, quantum cryptography has useful applications for governments and militaries as, historically, governments have kept military data secret for periods of over 60 years.
[
13
]
There also has been proof that quantum key distribution can travel through a noisy channel over a long distance and be secure. It can be reduced from a noisy quantum scheme to a classical noiseless scheme. This can be solved with classical probability theory.
[
16
]
This process of having consistent protection over a
noisy channel
can be possible through the implementation of quantum repeaters. Quantum repeaters have the ability to resolve quantum communication errors in an efficient way. Quantum repeaters, which are quantum computers, can be stationed as segments over the noisy channel to ensure the security of communication. Quantum repeaters do this by purifying the segments of the channel before connecting them creating a secure line of communication. Sub-par quantum repeaters can provide an efficient amount of security through the noisy channel over a long distance.
[
16
]

## Applications

Applications
[
edit
]
Quantum cryptography is a general subject that covers a broad range of cryptographic practices and protocols. While encryption techniques are widely recognized and understood, a significant challenge remains in the secure distribution of shared keys, often referred to as key establishment or key agreement.Quantum Key Distribution(QKD) aims to address this particular challenge. Below, we explore various notable methodologies and applications currently employed in quantum cryptography.

Quantum cryptography is a general subject that covers a broad range of cryptographic practices and protocols. While encryption techniques are widely recognized and understood, a significant challenge remains in the secure distribution of shared keys, often referred to as key establishment or key agreement.
Quantum Key Distribution
(QKD) aims to address this particular challenge. Below, we explore various notable methodologies and applications currently employed in quantum cryptography.
Main article:
Quantum key distribution
The best-known and developed application of quantum cryptography isQKD, which is the process of using quantum communication to establish a shared key between two parties (Alice and Bob, for example) without a third party (Eve) learning anything about that key, even if Eve can eavesdrop on all communication between Alice and Bob. If Eve tries to learn information about the key being established, discrepancies will arise causing Alice and Bob to notice. Once the key is established, it is then typically used forencryptedcommunication using classical techniques. For instance, the exchanged key could be used forsymmetric cryptography(e.g.one-time pad).

The best-known and developed application of quantum cryptography is
QKD
, which is the process of using quantum communication to establish a shared key between two parties (Alice and Bob, for example) without a third party (Eve) learning anything about that key, even if Eve can eavesdrop on all communication between Alice and Bob. If Eve tries to learn information about the key being established, discrepancies will arise causing Alice and Bob to notice. Once the key is established, it is then typically used for
encrypted
communication using classical techniques. For instance, the exchanged key could be used for
symmetric cryptography
(e.g.
one-time pad
).
The security of quantum key distribution can be proven mathematically without imposing any restrictions on the abilities of an eavesdropper, something not possible with classical key distribution. This is usually described as "unconditional security", although there are some minimal assumptions required, including that the laws of quantum mechanics apply and that Alice and Bob are able to authenticate each other, i.e. Eve should not be able to impersonate Alice or Bob as otherwise aman-in-the-middle attackwould be possible.

The security of quantum key distribution can be proven mathematically without imposing any restrictions on the abilities of an eavesdropper, something not possible with classical key distribution. This is usually described as "unconditional security", although there are some minimal assumptions required, including that the laws of quantum mechanics apply and that Alice and Bob are able to authenticate each other, i.e. Eve should not be able to impersonate Alice or Bob as otherwise a
man-in-the-middle attack
would be possible.
While QKD is secure, its practical application faces some challenges. There are in fact limitations for the key generation rate at increasing transmission distances.[17][18][19]Recent studies have allowed important advancements in this regard. In 2018, the protocol of twin-field QKD[20]was proposed as a mechanism to overcome the limits of lossy communication. The rate of the twin field protocol was shown to overcome the secret key-agreement capacity of the lossy communication channel, known as repeater-less PLOB bound,[19]at 340km of optical fiber; its ideal rate surpasses this bound already at 200km and follows the rate-loss scaling of the higher repeater-assisted secret key-agreement capacity[21](see figure 1 of[20]and figure 11 of[2]for more details). The protocol suggests that optimal key rates are achievable on "550 kilometers of standardoptical fibre", which is already commonly used in communications today. The theoretical result was confirmed in the first experimental demonstration of QKD beyond the PLOB bound which has been characterized as the firsteffectivequantum repeater.[22]Notable developments in terms of achieving high rates at long distances are the sending-not-sending (SNS) version of the TF-QKD protocol.[23][24]and the no-phase-postselected twin-field scheme.[25]

While QKD is secure, its practical application faces some challenges. There are in fact limitations for the key generation rate at increasing transmission distances.
[
17
]
[
18
]
[
19
]
Recent studies have allowed important advancements in this regard. In 2018, the protocol of twin-field QKD
[
20
]
was proposed as a mechanism to overcome the limits of lossy communication. The rate of the twin field protocol was shown to overcome the secret key-agreement capacity of the lossy communication channel, known as repeater-less PLOB bound,
[
19
]
at 340
km of optical fiber; its ideal rate surpasses this bound already at 200
km and follows the rate-loss scaling of the higher repeater-assisted secret key-agreement capacity
[
21
]
(see figure 1 of
[
20
]
and figure 11 of
[
2
]
for more details). The protocol suggests that optimal key rates are achievable on "550 kilometers of standard
optical fibre
", which is already commonly used in communications today. The theoretical result was confirmed in the first experimental demonstration of QKD beyond the PLOB bound which has been characterized as the first
effective
quantum repeater.
[
22
]
Notable developments in terms of achieving high rates at long distances are the sending-not-sending (SNS) version of the TF-QKD protocol.
[
23
]
[
24
]
and the no-phase-postselected twin-field scheme.
[
25
]

### Mistrustful quantum cryptography

Mistrustful quantum cryptography
[
edit
]
In mistrustful cryptography the participating parties do not trust each other. For example, Alice and Bob collaborate to perform some computation where both parties enter some private inputs. But Alice does not trust Bob and Bob does not trust Alice. Thus, a secure implementation of a cryptographic task requires that after completing the computation, Alice can be guaranteed that Bob has not cheated and Bob can be guaranteed that Alice has not cheated either. Examples of tasks in mistrustful cryptography arecommitment schemesandsecure computations, the latter including the further examples of coin flipping andoblivious transfer.Key distributiondoes not belong to the area of mistrustful cryptography. Mistrustful quantum cryptography studies the area of mistrustful cryptography usingquantum systems.

In mistrustful cryptography the participating parties do not trust each other. For example, Alice and Bob collaborate to perform some computation where both parties enter some private inputs. But Alice does not trust Bob and Bob does not trust Alice. Thus, a secure implementation of a cryptographic task requires that after completing the computation, Alice can be guaranteed that Bob has not cheated and Bob can be guaranteed that Alice has not cheated either. Examples of tasks in mistrustful cryptography are
commitment schemes
and
secure computations
, the latter including the further examples of coin flipping and
oblivious transfer
.
Key distribution
does not belong to the area of mistrustful cryptography. Mistrustful quantum cryptography studies the area of mistrustful cryptography using
quantum systems
.
In contrast toquantum key distributionwhere unconditional security can be achieved based only on the laws ofquantum physics, in the case of various tasks in mistrustful cryptography there are no-go theorems showing that it is impossible to achieve unconditionally secure protocols based only on the laws ofquantum physics. However, some of these tasks can be implemented with unconditional security if the protocols not only exploitquantum mechanicsbut alsospecial relativity. For example, unconditionally securequantum bitcommitment was shown impossible by Mayers[26]and by Lo and Chau.[27]Unconditionally secure ideal quantum coin flipping was shown impossible by Lo and Chau.[28]Moreover, Lo showed that there cannot be unconditionally secure quantum protocols for one-out-of-two oblivious transfer and other secure two-party computations.[29]However, unconditionally secure relativistic protocols for coin flipping and bit-commitment have been shown by Kent.[30][31]

In contrast to
quantum key distribution
where unconditional security can be achieved based only on the laws of
quantum physics
, in the case of various tasks in mistrustful cryptography there are no-go theorems showing that it is impossible to achieve unconditionally secure protocols based only on the laws of
quantum physics
. However, some of these tasks can be implemented with unconditional security if the protocols not only exploit
quantum mechanics
but also
special relativity
. For example, unconditionally secure
quantum bit
commitment was shown impossible by Mayers
[
26
]
and by Lo and Chau.
[
27
]
Unconditionally secure ideal quantum coin flipping was shown impossible by Lo and Chau.
[
28
]
Moreover, Lo showed that there cannot be unconditionally secure quantum protocols for one-out-of-two oblivious transfer and other secure two-party computations.
[
29
]
However, unconditionally secure relativistic protocols for coin flipping and bit-commitment have been shown by Kent.
[
30
]
[
31
]

#### Quantum coin flipping

Quantum coin flipping
[
edit
]
Main article:
Quantum coin flipping
Alice decides her random basis and sequence of qubits. She then sends the qubits as photons to Bob via the quantum channel. Bob detects these qubits and records his results in a table. Based on the table, Bob makes his guess to Alice on what basis she used.
Unlike quantum key distribution,quantum coin flippingis a protocol that is used between two participants who do not trust each other.[32]The participants communicate via a quantum channel and exchange information through the transmission ofqubits.[33]But because Alice and Bob do not trust each other, each expects the other to cheat. Therefore, more effort must be spent on ensuring that neither Alice nor Bob can gain a significant advantage over the other to produce a desired outcome. An ability to influence a particular outcome is referred to as a bias, and there is a significant focus on developing protocols to reduce the bias of a dishonest player,[34][35]otherwise known as cheating. Quantum communication protocols, including quantum coin flipping, have been shown to provide significant security advantages over classical communication, though they may be considered difficult to realize in the practical world.[32]

Unlike quantum key distribution,
quantum coin flipping
is a protocol that is used between two participants who do not trust each other.
[
32
]
The participants communicate via a quantum channel and exchange information through the transmission of
qubits
.
[
33
]
But because Alice and Bob do not trust each other, each expects the other to cheat. Therefore, more effort must be spent on ensuring that neither Alice nor Bob can gain a significant advantage over the other to produce a desired outcome. An ability to influence a particular outcome is referred to as a bias, and there is a significant focus on developing protocols to reduce the bias of a dishonest player,
[
34
]
[
35
]
otherwise known as cheating. Quantum communication protocols, including quantum coin flipping, have been shown to provide significant security advantages over classical communication, though they may be considered difficult to realize in the practical world.
[
32
]
A coin flip protocol generally occurs like this:[36]

A coin flip protocol generally occurs like this:
[
36
]
- Alice chooses a basis (either rectilinear or diagonal) and generates a string of photons to send to Bob in that basis.
Alice chooses a basis (either rectilinear or diagonal) and generates a string of photons to send to Bob in that basis.
- Bob randomly chooses to measure each photon in a rectilinear or diagonal basis, noting which basis he used and the measured value.
Bob randomly chooses to measure each photon in a rectilinear or diagonal basis, noting which basis he used and the measured value.
- Bob publicly guesses which basis Alice used to send her qubits.
Bob publicly guesses which basis Alice used to send her qubits.
- Alice announces the basis she used and sends her original string to Bob.
Alice announces the basis she used and sends her original string to Bob.
- Bob confirms by comparing Alice's string to his table. It should be perfectly correlated with the values Bob measured using Alice's basis and completely uncorrelated with the opposite.
Bob confirms by comparing Alice's string to his table. It should be perfectly correlated with the values Bob measured using Alice's basis and completely uncorrelated with the opposite.
Cheating occurs when one player attempts to influence, or increase the probability of a particular outcome. The protocol discourages some forms of cheating; for example, Alice could cheat at step 4 by claiming that Bob incorrectly guessed her initial basis when he guessed correctly, but Alice would then need to generate a new string of qubits that perfectly correlates with what Bob measured in the opposite table.[36]Her chance of generating a matching string of qubits will decrease exponentially with the number of qubits sent, and if Bob notes a mismatch, he will know she was lying. Alice could also generate a string of photons using a mixture of states, but Bob would easily see that her string will correlate partially (but not fully) with both sides of the table, and know she cheated in the process.[36]There is also an inherent flaw that comes with current quantum devices. Errors and lost qubits will affect Bob's measurements, resulting in holes in Bob's measurement table. Significant losses in measurement will affect Bob's ability to verify Alice's qubit sequence in step 5.

Cheating occurs when one player attempts to influence, or increase the probability of a particular outcome. The protocol discourages some forms of cheating; for example, Alice could cheat at step 4 by claiming that Bob incorrectly guessed her initial basis when he guessed correctly, but Alice would then need to generate a new string of qubits that perfectly correlates with what Bob measured in the opposite table.
[
36
]
Her chance of generating a matching string of qubits will decrease exponentially with the number of qubits sent, and if Bob notes a mismatch, he will know she was lying. Alice could also generate a string of photons using a mixture of states, but Bob would easily see that her string will correlate partially (but not fully) with both sides of the table, and know she cheated in the process.
[
36
]
There is also an inherent flaw that comes with current quantum devices. Errors and lost qubits will affect Bob's measurements, resulting in holes in Bob's measurement table. Significant losses in measurement will affect Bob's ability to verify Alice's qubit sequence in step 5.
One theoretically surefire way for Alice to cheat is to utilize theEinstein-Podolsky-Rosen (EPR) paradox. Two photons in an EPR pair are anticorrelated; that is, they will always be found to have opposite polarizations, provided that they are measured in the same basis. Alice could generate a string of EPR pairs, sending one photon per pair to Bob and storing the other herself. When Bob states his guess, she could measure her EPR pair photons in the opposite basis and obtain a perfect correlation to Bob's opposite table.[36]Bob would never know she cheated. However, this requires capabilities that quantum technology currently does not possess, making it impossible to do in practice. To successfully execute this, Alice would need to be able to store all the photons for a significant amount of time as well as measure them with near perfect efficiency. This is because any photon lost in storage or in measurement would result in a hole in her string that she would have to fill by guessing. The more guesses she has to make, the more she risks detection by Bob for cheating.

One theoretically surefire way for Alice to cheat is to utilize the
Einstein-Podolsky-Rosen (EPR) paradox
. Two photons in an EPR pair are anticorrelated; that is, they will always be found to have opposite polarizations, provided that they are measured in the same basis. Alice could generate a string of EPR pairs, sending one photon per pair to Bob and storing the other herself. When Bob states his guess, she could measure her EPR pair photons in the opposite basis and obtain a perfect correlation to Bob's opposite table.
[
36
]
Bob would never know she cheated. However, this requires capabilities that quantum technology currently does not possess, making it impossible to do in practice. To successfully execute this, Alice would need to be able to store all the photons for a significant amount of time as well as measure them with near perfect efficiency. This is because any photon lost in storage or in measurement would result in a hole in her string that she would have to fill by guessing. The more guesses she has to make, the more she risks detection by Bob for cheating.

#### Quantum commitment

Quantum commitment
[
edit
]
In addition to quantum coin-flipping, quantum commitment protocols are implemented when distrustful parties are involved. Acommitment schemeallows a party Alice to fix a certain value (to "commit") in such a way that Alice cannot change that value while at the same time ensuring that the recipient Bob cannot learn anything about that value until Alice reveals it. Such commitment schemes are commonly used in cryptographic protocols (e.g.Quantum coin flipping,Zero-knowledge proof,secure two-party computation, andOblivious transfer).

In addition to quantum coin-flipping, quantum commitment protocols are implemented when distrustful parties are involved. A
commitment scheme
allows a party Alice to fix a certain value (to "commit") in such a way that Alice cannot change that value while at the same time ensuring that the recipient Bob cannot learn anything about that value until Alice reveals it. Such commitment schemes are commonly used in cryptographic protocols (e.g.
Quantum coin flipping
,
Zero-knowledge proof
,
secure two-party computation
, and
Oblivious transfer
).
In the quantum setting, they would be particularly useful: Crépeau and Kilian showed that from a commitment and a quantum channel, one can construct an unconditionally secure protocol for performing so-calledoblivious transfer.[37]Oblivious transfer, on the other hand, had been shown by Kilian to allow implementation of almost any distributed computation in a secure way (so-calledsecure multi-party computation).[38](Note: The results by Crépeau and Kilian[37][38]together do not directly imply that given a commitment and a quantum channel one can perform secure multi-party computation. This is because the results do not guarantee "composability", that is, when plugging them together, one might lose security.)

In the quantum setting, they would be particularly useful: Crépeau and Kilian showed that from a commitment and a quantum channel, one can construct an unconditionally secure protocol for performing so-called
oblivious transfer
.
[
37
]
Oblivious transfer
, on the other hand, had been shown by Kilian to allow implementation of almost any distributed computation in a secure way (so-called
secure multi-party computation
).
[
38
]
(Note: The results by Crépeau and Kilian
[
37
]
[
38
]
together do not directly imply that given a commitment and a quantum channel one can perform secure multi-party computation. This is because the results do not guarantee "composability", that is, when plugging them together, one might lose security.)
Early quantum commitment protocols[39]were shown to be flawed. In fact, Mayers showed that (unconditionally secure) quantum commitment is impossible: a computationally unlimited attacker can break any quantum commitment protocol.[26]

Early quantum commitment protocols
[
39
]
were shown to be flawed. In fact, Mayers showed that (
unconditionally secure
) quantum commitment is impossible: a computationally unlimited attacker can break any quantum commitment protocol.
[
26
]
Yet, the result by Mayers does not preclude the possibility of constructing quantum commitment protocols (and thus secure multi-party computation protocols) under assumptions that are much weaker than the assumptions needed for commitment protocols that do not use quantum communication. The bounded quantum storage model described below is an example for a setting in which quantum communication can be used to construct commitment protocols. A breakthrough in November 2013 offers "unconditional" security of information by harnessing quantum theory and relativity, which has been successfully demonstrated on a global scale for the first time.[40]More recently, Wang et al., proposed another commitment scheme in which the "unconditional hiding" is perfect.[41]

Yet, the result by Mayers does not preclude the possibility of constructing quantum commitment protocols (and thus secure multi-party computation protocols) under assumptions that are much weaker than the assumptions needed for commitment protocols that do not use quantum communication. The bounded quantum storage model described below is an example for a setting in which quantum communication can be used to construct commitment protocols. A breakthrough in November 2013 offers "unconditional" security of information by harnessing quantum theory and relativity, which has been successfully demonstrated on a global scale for the first time.
[
40
]
More recently, Wang et al., proposed another commitment scheme in which the "unconditional hiding" is perfect.
[
41
]
Physical unclonable functionscan be also exploited for the construction of cryptographic commitments.[42]

Physical unclonable functions
can be also exploited for the construction of cryptographic commitments.
[
42
]

### Bounded- and noisy-quantum-storage model

Bounded- and noisy-quantum-storage model
[
edit
]
One possibility to construct unconditionally secure quantumcommitmentand quantumoblivious transfer(OT) protocols is to use the bounded quantum storage model (BQSM). In this model, it is assumed that the amount of quantum data that an adversary can store is limited by some known constant Q. However, no limit is imposed on the amount of classical (i.e., non-quantum) data the adversary may store.

One possibility to construct unconditionally secure quantum
commitment
and quantum
oblivious transfer
(OT) protocols is to use the bounded quantum storage model (BQSM). In this model, it is assumed that the amount of quantum data that an adversary can store is limited by some known constant Q. However, no limit is imposed on the amount of classical (i.e., non-quantum) data the adversary may store.
In the BQSM, one can construct commitment and oblivious transfer protocols.[43]The underlying idea is the following: The protocol parties exchange more than Q quantum bits (qubits). Since even a dishonest party cannot store all that information (the quantum memory of the adversary is limited to Q qubits), a large part of the data will have to be either measured or discarded. Forcing dishonest parties to measure a large part of the data allows the protocol to circumvent the impossibility result, commitment and oblivious transfer protocols can now be implemented.[26]

In the BQSM, one can construct commitment and oblivious transfer protocols.
[
43
]
The underlying idea is the following: The protocol parties exchange more than Q quantum bits (
qubits
). Since even a dishonest party cannot store all that information (the quantum memory of the adversary is limited to Q qubits), a large part of the data will have to be either measured or discarded. Forcing dishonest parties to measure a large part of the data allows the protocol to circumvent the impossibility result, commitment and oblivious transfer protocols can now be implemented.
[
26
]
The protocols in the BQSM presented byDamgård, Fehr, Salvail, and Schaffner[43]do not assume that honest protocol participants store any quantum information; the technical requirements are similar to those inquantum key distributionprotocols. These protocols can thus, at least in principle, be realized with today's technology. The communication complexity is only a constant factor larger than the bound Q on the adversary's quantum memory.

The protocols in the BQSM presented by
Damgård
, Fehr, Salvail, and Schaffner
[
43
]
do not assume that honest protocol participants store any quantum information; the technical requirements are similar to those in
quantum key distribution
protocols. These protocols can thus, at least in principle, be realized with today's technology. The communication complexity is only a constant factor larger than the bound Q on the adversary's quantum memory.
The advantage of the BQSM is that the assumption that the adversary's quantum memory is limited is quite realistic. With today's technology, storing even a single qubit reliably over a sufficiently long time is difficult. (What "sufficiently long" means depends on the protocol details. By introducing an artificial pause in the protocol, the amount of time over which the adversary needs to store quantum data can be made arbitrarily large.)

The advantage of the BQSM is that the assumption that the adversary's quantum memory is limited is quite realistic. With today's technology, storing even a single qubit reliably over a sufficiently long time is difficult. (What "sufficiently long" means depends on the protocol details. By introducing an artificial pause in the protocol, the amount of time over which the adversary needs to store quantum data can be made arbitrarily large.)
An extension of the BQSM is thenoisy-storage modelintroduced byWehner, Schaffner andTerhal.[44]Instead of considering an upper bound on the physical size of the adversary's quantum memory, an adversary is allowed to use imperfect quantum storage devices of arbitrary size. The level of imperfection is modelled by noisy quantum channels. For high enough noise levels, the same primitives as in the BQSM can be achieved[45]and the BQSM forms a special case of the noisy-storage model.

An extension of the BQSM is the
noisy-storage model
introduced by
Wehner
, Schaffner and
Terhal
.
[
44
]
Instead of considering an upper bound on the physical size of the adversary's quantum memory, an adversary is allowed to use imperfect quantum storage devices of arbitrary size. The level of imperfection is modelled by noisy quantum channels. For high enough noise levels, the same primitives as in the BQSM can be achieved
[
45
]
and the BQSM forms a special case of the noisy-storage model.
In the classical setting, similar results can be achieved when assuming a bound on the amount of classical (non-quantum) data that the adversary can store.[46]It was proven, however, that in this model also the honest parties have to use a large amount of memory (namely the square-root of the adversary's memory bound).[47]This makes these protocols impractical for realistic memory bounds. (Note that with today's technology such as hard disks, an adversary can cheaply store large amounts of classical data.)

In the classical setting, similar results can be achieved when assuming a bound on the amount of classical (non-quantum) data that the adversary can store.
[
46
]
It was proven, however, that in this model also the honest parties have to use a large amount of memory (namely the square-root of the adversary's memory bound).
[
47
]
This makes these protocols impractical for realistic memory bounds. (Note that with today's technology such as hard disks, an adversary can cheaply store large amounts of classical data.)

### Position-based quantum cryptography

Position-based quantum cryptography
[
edit
]
See also:
Non-local quantum computation
The goal of position-based quantum cryptography is to use thegeographical locationof a player as its (only) credential. For example, one wants to send a message to a player at a specified position with the guarantee that it can only be read if the receiving party is located at that particular position. In the basic task ofposition-verification, a player, Alice, wants to convince the (honest) verifiers that she is located at a particular point. It has been shown by Chandranet al.that position-verification using classical protocols is impossible against colluding adversaries (who control all positions except the prover's claimed position).[48]Under various restrictions on the adversaries, schemes are possible.

The goal of position-based quantum cryptography is to use the
geographical location
of a player as its (only) credential. For example, one wants to send a message to a player at a specified position with the guarantee that it can only be read if the receiving party is located at that particular position. In the basic task of
position-verification
, a player, Alice, wants to convince the (honest) verifiers that she is located at a particular point. It has been shown by Chandran
et al.
that position-verification using classical protocols is impossible against colluding adversaries (who control all positions except the prover's claimed position).
[
48
]
Under various restrictions on the adversaries, schemes are possible.
Under the name of 'quantum tagging', the first position-based quantum schemes have been investigated in 2002 by Kent. A US-patent[49]was granted in 2006. The notion of using quantum effects for location verification first appeared in the scientific literature in 2010.[50][51]After several other quantum protocols for position verification have been suggested in 2010,[52][53]Buhrman et al. claimed a general impossibility result:[54]using an enormous amount ofquantum entanglement(they use a doubly exponential number ofEPR pairs, in the number of qubits the honest player operates on), colluding adversaries are always able to make it look to the verifiers as if they were at the claimed position. However, this result does not exclude the possibility of practical schemes in the bounded- or noisy-quantum-storage model (see above). Later Beigi and König improved the amount of EPR pairs needed in the general attack against position-verification protocols to exponential. They also showed that a particular protocol remains secure against adversaries who controls only a linear amount of EPR pairs.[55]It is argued in[56]that due to time-energy coupling the possibility of formal unconditional location verification via quantum effects remains an open problem. The study of position-based quantum cryptography also has connections with the protocol of port-based quantum teleportation, which is a more advanced version ofquantum teleportation, where many EPR pairs are simultaneously used as ports.

Under the name of 'quantum tagging', the first position-based quantum schemes have been investigated in 2002 by Kent. A US-patent
[
49
]
was granted in 2006. The notion of using quantum effects for location verification first appeared in the scientific literature in 2010.
[
50
]
[
51
]
After several other quantum protocols for position verification have been suggested in 2010,
[
52
]
[
53
]
Buhrman et al. claimed a general impossibility result:
[
54
]
using an enormous amount of
quantum entanglement
(they use a doubly exponential number of
EPR pairs
, in the number of qubits the honest player operates on), colluding adversaries are always able to make it look to the verifiers as if they were at the claimed position. However, this result does not exclude the possibility of practical schemes in the bounded- or noisy-quantum-storage model (see above). Later Beigi and König improved the amount of EPR pairs needed in the general attack against position-verification protocols to exponential. They also showed that a particular protocol remains secure against adversaries who controls only a linear amount of EPR pairs.
[
55
]
It is argued in
[
56
]
that due to time-energy coupling the possibility of formal unconditional location verification via quantum effects remains an open problem. The study of position-based quantum cryptography also has connections with the protocol of port-based quantum teleportation, which is a more advanced version of
quantum teleportation
, where many EPR pairs are simultaneously used as ports.

### Device-independent quantum cryptography

Device-independent quantum cryptography
[
edit
]
Main article:
Device-independent quantum cryptography
A quantum cryptographic protocol isdevice-independentif its security does not rely on trusting that the quantum devices used are truthful. Thus the security analysis of such a protocol needs to consider scenarios of imperfect or even malicious devices.[57]Mayers and Yao[58]proposed the idea of designing quantum protocols using "self-testing" quantum apparatus, the internal operations of which can be uniquely determined by their input-output statistics. Subsequently, Roger Colbeck in his Thesis[59]proposed the use ofBell testsfor checking the honesty of the devices. Since then, several problems have been shown to admit unconditional secure and device-independent protocols, even when the actual devices performing the Bell test are substantially "noisy", i.e., far from being ideal. These problems includequantum key distribution,[60][61]randomness expansion,[61][62]andrandomness amplification.[63]

A quantum cryptographic protocol is
device-independent
if its security does not rely on trusting that the quantum devices used are truthful. Thus the security analysis of such a protocol needs to consider scenarios of imperfect or even malicious devices.
[
57
]
Mayers and Yao
[
58
]
proposed the idea of designing quantum protocols using "self-testing" quantum apparatus, the internal operations of which can be uniquely determined by their input-output statistics. Subsequently, Roger Colbeck in his Thesis
[
59
]
proposed the use of
Bell tests
for checking the honesty of the devices. Since then, several problems have been shown to admit unconditional secure and device-independent protocols, even when the actual devices performing the Bell test are substantially "noisy", i.e., far from being ideal. These problems include
quantum key distribution
,
[
60
]
[
61
]
randomness expansion
,
[
61
]
[
62
]
and
randomness amplification
.
[
63
]
In 2018, theoretical studies performed by Arnon- Friedman et al. suggest that exploiting a property of entropy that is later referred to as "Entropy Accumulation Theorem (EAT)", an extension ofAsymptotic equipartition property, can guarantee the security of a device independent protocol.[64]

In 2018, theoretical studies performed by Arnon- Friedman et al. suggest that exploiting a property of entropy that is later referred to as "Entropy Accumulation Theorem (EAT)", an extension of
Asymptotic equipartition property
, can guarantee the security of a device independent protocol.
[
64
]

## Post-quantum cryptography

Post-quantum cryptography
[
edit
]
Main article:
Post-quantum cryptography
Cryptographically-relevantquantum computersmay become a technological reality; it is therefore important to study cryptographic schemes used against adversaries with access to a quantum computer. The study of such schemes is often referred to aspost-quantum cryptography. The need for post-quantum cryptography arises from the fact that many popular encryption and signature schemes, mainly those based onECCandRSA, can be broken usingShor's algorithmforfactoringand computingdiscrete logarithmson a quantum computer. Examples for schemes that are, as of today's knowledge, secure against quantum adversaries areMcElieceandlattice-basedschemes, as well as mostsymmetric-key algorithms.[65][66]Surveys of post-quantum cryptography are available.[67][68]

Cryptographically-relevant
quantum computers
may become a technological reality; it is therefore important to study cryptographic schemes used against adversaries with access to a quantum computer. The study of such schemes is often referred to as
post-quantum cryptography
. The need for post-quantum cryptography arises from the fact that many popular encryption and signature schemes, mainly those based on
ECC
and
RSA
, can be broken using
Shor's algorithm
for
factoring
and computing
discrete logarithms
on a quantum computer. Examples for schemes that are, as of today's knowledge, secure against quantum adversaries are
McEliece
and
lattice-based
schemes, as well as most
symmetric-key algorithms
.
[
65
]
[
66
]
Surveys of post-quantum cryptography are available.
[
67
]
[
68
]
Additional research was made into how existing cryptographic techniques have to be modified to be able to cope with quantum adversaries. For example, when trying to developzero-knowledge proof systemsthat are secure against quantum adversaries, new techniques need to be used: In a classical setting, the analysis of a zero-knowledge proof system usually involves "rewinding", a technique that makes it necessary to copy the internal state of the adversary. In a quantum setting, copying a state is not always possible (no-cloning theorem); a variant of the rewinding technique has to be used.[69]

Additional research was made into how existing cryptographic techniques have to be modified to be able to cope with quantum adversaries. For example, when trying to develop
zero-knowledge proof systems
that are secure against quantum adversaries, new techniques need to be used: In a classical setting, the analysis of a zero-knowledge proof system usually involves "rewinding", a technique that makes it necessary to copy the internal state of the adversary. In a quantum setting, copying a state is not always possible (
no-cloning theorem
); a variant of the rewinding technique has to be used.
[
69
]
Post-quantum algorithms are also called "quantum resistant", because – unlike quantum key distribution – it is not known or provable that there will not be potential future quantum attacks against them. Even though they may possibly be vulnerable to quantum attacks in the future, the NSA is announcing plans to transition to quantum resistant algorithms.[70]The National Institute of Standards and Technology (NIST) believes that it is time to think of quantum-safe primitives.[71]

Post-quantum algorithms are also called "quantum resistant", because – unlike quantum key distribution – it is not known or provable that there will not be potential future quantum attacks against them. Even though they may possibly be vulnerable to quantum attacks in the future, the NSA is announcing plans to transition to quantum resistant algorithms.
[
70
]
The National Institute of Standards and Technology (
NIST
) believes that it is time to think of quantum-safe primitives.
[
71
]

## Quantum cryptography beyond key distribution

Quantum cryptography beyond key distribution
[
edit
]
So far, quantum cryptography has been mainly identified with the development of quantum key distribution protocols.Symmetriccryptosystems with keys that have been distributed by means of quantum key distribution become inefficient for large networks (many users), because of the necessity for the establishment and the manipulation of many pairwise secret keys (the so-called "key-management problem"). Moreover, this distribution alone does not address many other cryptographic tasks and functions, which are of vital importance in everyday life. Kak's three-stage protocol has been proposed as a method for secure communication that is entirely quantum unlike quantum key distribution, in which the cryptographic transformation uses classical algorithms.[72]

So far, quantum cryptography has been mainly identified with the development of quantum key distribution protocols.
Symmetric
cryptosystems with keys that have been distributed by means of quantum key distribution become inefficient for large networks (many users), because of the necessity for the establishment and the manipulation of many pairwise secret keys (the so-called "key-management problem"). Moreover, this distribution alone does not address many other cryptographic tasks and functions, which are of vital importance in everyday life. Kak's three-stage protocol has been proposed as a method for secure communication that is entirely quantum unlike quantum key distribution, in which the cryptographic transformation uses classical algorithms.
[
72
]
Besides quantum commitment and oblivious transfer (discussed above), research on quantum cryptography beyond key distribution revolves around quantum message authentication,[73]quantum digital signatures,[74][75]quantum one-way functions and public-key encryption,[76][77][78][79][80][81][82]quantum key-exchange,[83]quantum fingerprinting[84]and entity authentication[85][86][87](for example, seeQuantum readout of PUFs), etc.

Besides quantum commitment and oblivious transfer (discussed above), research on quantum cryptography beyond key distribution revolves around quantum message authentication,
[
73
]
quantum digital signatures,
[
74
]
[
75
]
quantum one-way functions and public-key encryption,
[
76
]
[
77
]
[
78
]
[
79
]
[
80
]
[
81
]
[
82
]
quantum key-exchange,
[
83
]
quantum fingerprinting
[
84
]
and entity authentication
[
85
]
[
86
]
[
87
]
(for example, see
Quantum readout of PUFs
), etc.

## Y-00 protocol

Y-00 protocol
[
edit
]
H. P. Yuen presented Y-00 as a stream cipher using quantum noise around 2000 and applied it for the U.S. Defense Advanced Research Projects Agency (DARPA) High-Speed and High-Capacity Quantum Cryptography Project as an alternative to quantum key distribution.[88][89]The review paper summarizes it well.[90]

H. P. Yuen presented Y-00 as a stream cipher using quantum noise around 2000 and applied it for the U.S. Defense Advanced Research Projects Agency (
DARPA
) High-Speed and High-Capacity Quantum Cryptography Project as an alternative to quantum key distribution.
[
88
]
[
89
]
The review paper summarizes it well.
[
90
]
Unlike quantum key distribution protocols, the main purpose of Y-00 is to transmit a message without eavesdrop-monitoring, not to distribute a key. Therefore,privacy amplificationmay be used only for key distributions.[91]Currently, research is being conducted mainly in Japan and China: e.g.[92][93]

Unlike quantum key distribution protocols, the main purpose of Y-00 is to transmit a message without eavesdrop-monitoring, not to distribute a key. Therefore,
privacy amplification
may be used only for key distributions.
[
91
]
Currently, research is being conducted mainly in Japan and China: e.g.
[
92
]
[
93
]
The principle of operation is as follows. First, legitimate users share a key and change it to a pseudo-random keystream using the same pseudo-random number generator. Then, the legitimate parties can perform conventional optical communications based on the shared key by transforming it appropriately. For attackers who do not share the key, the wire-tap channel model ofAaron D. Wyneris implemented. The legitimate users' advantage based on the shared key is called "advantage creation". The goal is to achieve longer covert communication than theinformation-theoretic securitylimit (one-time pad) set by Shannon.[94]The source of the noise in the above wire-tap channel is the uncertainty principle of the electromagnetic field itself, which is a theoretical consequence of the theory of laser described byRoy J. GlauberandE. C. George Sudarshan(coherent state).[95][96][97]Therefore, existing optical communication technologies are sufficient for implementation that some reviews describes: e.g.[90]Furthermore, since it uses ordinary communication laser light, it is compatible with existing communication infrastructure and can be used for high-speed 
and long-distance communication and routing.[98][99][100][101][102]

The principle of operation is as follows. First, legitimate users share a key and change it to a pseudo-random keystream using the same pseudo-random number generator. Then, the legitimate parties can perform conventional optical communications based on the shared key by transforming it appropriately. For attackers who do not share the key, the wire-tap channel model of
Aaron D. Wyner
is implemented. The legitimate users' advantage based on the shared key is called "advantage creation". The goal is to achieve longer covert communication than the
information-theoretic security
limit (
one-time pad
) set by Shannon.
[
94
]
The source of the noise in the above wire-tap channel is the uncertainty principle of the electromagnetic field itself, which is a theoretical consequence of the theory of laser described by
Roy J. Glauber
and
E. C. George Sudarshan
(
coherent state
).
[
95
]
[
96
]
[
97
]
Therefore, existing optical communication technologies are sufficient for implementation that some reviews describes: e.g.
[
90
]
Furthermore, since it uses ordinary communication laser light, it is compatible with existing communication infrastructure and can be used for high-speed 
and long-distance communication and routing.
[
98
]
[
99
]
[
100
]
[
101
]
[
102
]
Although the main purpose of the protocol is to transmit the message, key distribution is possible by simply replacing the message with a key.[103][91]Since it is a symmetric key cipher, it must share the initial key previously; however, a method of the initial key agreement was also proposed.[104]

Although the main purpose of the protocol is to transmit the message, key distribution is possible by simply replacing the message with a key.
[
103
]
[
91
]
Since it is a symmetric key cipher, it must share the initial key previously; however, a method of the initial key agreement was also proposed.
[
104
]
On the other hand, it is currently unclear what implementation realizesinformation-theoretic security, and security of this protocol has long been a matter of debate.[105][106][107][108][109][110][111][112][113][114]

On the other hand, it is currently unclear what implementation realizes
information-theoretic security
, and security of this protocol has long been a matter of debate.
[
105
]
[
106
]
[
107
]
[
108
]
[
109
]
[
110
]
[
111
]
[
112
]
[
113
]
[
114
]

## Implementation in practice

Implementation in practice
[
edit
]
In theory, quantum cryptography seems to be a successful turning point in theinformation securitysector. However, no cryptographic method can ever be absolutely secure.[115]In practice, quantum cryptography is only conditionally secure, dependent on a key set of assumptions.[116]

In theory, quantum cryptography seems to be a successful turning point in the
information security
sector. However, no cryptographic method can ever be absolutely secure.
[
115
]
In practice, quantum cryptography is only conditionally secure, dependent on a key set of assumptions.
[
116
]

### Single-photon source assumption

Single-photon source assumption
[
edit
]
The theoretical basis for quantum key distribution assumes the use of single-photon sources. However, such sources are difficult to construct, and most real-world quantum cryptography systems use faint laser sources as a medium for information transfer.[116]These multi-photon sources open the possibility for eavesdropper attacks, particularly a photon splitting attack.[117]An eavesdropper, Eve, can split the multi-photon source and retain one copy for herself.[117]The other photons are then transmitted to Bob without any measurement or trace that Eve captured a copy of the data.[117]Scientists believe they can retain security with a multi-photon source by using decoy states that test for the presence of an eavesdropper.[117]However, in 2016, scientists developed a near perfect single photon source and estimate that one could be developed in the near future.[118]

The theoretical basis for quantum key distribution assumes the use of single-photon sources. However, such sources are difficult to construct, and most real-world quantum cryptography systems use faint laser sources as a medium for information transfer.
[
116
]
These multi-photon sources open the possibility for eavesdropper attacks, particularly a photon splitting attack.
[
117
]
An eavesdropper, Eve, can split the multi-photon source and retain one copy for herself.
[
117
]
The other photons are then transmitted to Bob without any measurement or trace that Eve captured a copy of the data.
[
117
]
Scientists believe they can retain security with a multi-photon source by using decoy states that test for the presence of an eavesdropper.
[
117
]
However, in 2016, scientists developed a near perfect single photon source and estimate that one could be developed in the near future.
[
118
]

### Identical detector efficiency assumption

Identical detector efficiency assumption
[
edit
]
In practice, multiple single-photon detectors are used in quantum key distribution devices, one for Alice and one for Bob.[116]These photodetectors are tuned to detect an incoming photon during a short window of only a few nanoseconds.[119]Due to manufacturing differences between the two detectors, their respective detection windows will be shifted by some finite amount.[119]An eavesdropper, Eve, can take advantage of this detector inefficiency by measuring Alice's qubit and sending a "fake state" to Bob.[119]Eve first captures the photon sent by Alice and then generates another photon to send to Bob.[119]Eve manipulates the phase and timing of the "faked" photon in a way that prevents Bob from detecting the presence of an eavesdropper.[119]The only way to eliminate this vulnerability is to eliminate differences in photodetector efficiency, which is difficult to do given finite manufacturing tolerances that cause optical path length differences, wire length differences, and other defects.[119]

In practice, multiple single-photon detectors are used in quantum key distribution devices, one for Alice and one for Bob.
[
116
]
These photodetectors are tuned to detect an incoming photon during a short window of only a few nanoseconds.
[
119
]
Due to manufacturing differences between the two detectors, their respective detection windows will be shifted by some finite amount.
[
119
]
An eavesdropper, Eve, can take advantage of this detector inefficiency by measuring Alice's qubit and sending a "fake state" to Bob.
[
119
]
Eve first captures the photon sent by Alice and then generates another photon to send to Bob.
[
119
]
Eve manipulates the phase and timing of the "faked" photon in a way that prevents Bob from detecting the presence of an eavesdropper.
[
119
]
The only way to eliminate this vulnerability is to eliminate differences in photodetector efficiency, which is difficult to do given finite manufacturing tolerances that cause optical path length differences, wire length differences, and other defects.
[
119
]

### Deprecation of quantum key distributions from governmental institutions

Deprecation of quantum key distributions from governmental institutions
[
edit
]
Given the practical challenges raised below, several organizations recommend using "post-quantum cryptography (or quantum-resistant cryptography)" instead of quantum key distribution.

Given the practical challenges raised below, several organizations recommend using "post-quantum cryptography (or quantum-resistant cryptography)" instead of quantum key distribution.
- USANational Security Agency,[120]
USA
National Security Agency
,
[
120
]
- European Union Agency for Cybersecurityof EU (ENISA),[121]
European Union Agency for Cybersecurity
of EU (ENISA),
[
121
]
- United Kingdom'sNational Cyber Security Centre,[122]
United Kingdom's
National Cyber Security Centre
,
[
122
]
- French Secretariat for Defense and Security (ANSSI),[123]
French Secretariat for Defense and Security (ANSSI),
[
123
]
- German Federal Office for Information Security (BSI)[124]
German Federal Office for Information Security (BSI)
[
124
]
- Australia's ASD[125]
Australia's ASD
[
125
]
- Netherland National Communications Security Agency (NLNCSA)
Netherland National Communications Security Agency (NLNCSA)
- and Swedish National Communications Security Authority, Swedish Armed Forces[126]For example, the US National Security Agency addresses five issues:[120]
and Swedish National Communications Security Authority, Swedish Armed Forces
[
126
]
For example, the US National Security Agency addresses five issues:
[
120
]
- Quantum key distribution is only a partial solution. QKD generates keying material for an encryption algorithm that provides confidentiality. Such keying material could also be used in symmetric key cryptographic algorithms to provide integrity and authentication if one has the cryptographic assurance that the original QKD transmission comes from the desired entity (i.e. entity source authentication). QKD does not provide a means to authenticate the QKD transmission source. Therefore, source authentication requires the use of asymmetric cryptography or pre-placed keys to provide that authentication. Moreover, the confidentiality services QKD offers can be provided by quantum-resistant cryptography, which is typically less expensive with a better understood risk profile.
Quantum key distribution is only a partial solution. QKD generates keying material for an encryption algorithm that provides confidentiality. Such keying material could also be used in symmetric key cryptographic algorithms to provide integrity and authentication if one has the cryptographic assurance that the original QKD transmission comes from the desired entity (i.e. entity source authentication). QKD does not provide a means to authenticate the QKD transmission source. Therefore, source authentication requires the use of asymmetric cryptography or pre-placed keys to provide that authentication. Moreover, the confidentiality services QKD offers can be provided by quantum-resistant cryptography, which is typically less expensive with a better understood risk profile.
- Quantum key distribution requires special purpose equipment. QKD is based on physical properties, and its security derives from unique physical layer communications. This requires users to lease dedicated fiber connections or physically manage free-space transmitters. It cannot be implemented in software or as a service on a network, and cannot be easily integrated into existing network equipment. Since QKD is hardware-based it also lacks flexibility for upgrades or security patches.
Quantum key distribution requires special purpose equipment. QKD is based on physical properties, and its security derives from unique physical layer communications. This requires users to lease dedicated fiber connections or physically manage free-space transmitters. It cannot be implemented in software or as a service on a network, and cannot be easily integrated into existing network equipment. Since QKD is hardware-based it also lacks flexibility for upgrades or security patches.
- Quantum key distribution increases infrastructure costs and insider-threat risks. QKD networks frequently necessitate the use of trusted relays, entailing additional cost for secure facilities and additional security risk from insider threats. This eliminates many use cases from consideration.
Quantum key distribution increases infrastructure costs and insider-threat risks. QKD networks frequently necessitate the use of trusted relays, entailing additional cost for secure facilities and additional security risk from insider threats. This eliminates many use cases from consideration.
- Securing and validating quantum key distribution is a significant challenge. The actual security provided by a QKD system is not the theoretical unconditional security from the laws of physics (as modeled and often suggested), but rather the more limited security that can be achieved by hardware and engineering designs. The tolerance for error in cryptographic security, however, is many orders of magnitude smaller than what is available in most physical engineering scenarios, making it very difficult to validate. The specific hardware used to perform QKD can introduce vulnerabilities, resulting in several well-publicized attacks on commercial QKD systems.[127]
Securing and validating quantum key distribution is a significant challenge. The actual security provided by a QKD system is not the theoretical unconditional security from the laws of physics (as modeled and often suggested), but rather the more limited security that can be achieved by hardware and engineering designs. The tolerance for error in cryptographic security, however, is many orders of magnitude smaller than what is available in most physical engineering scenarios, making it very difficult to validate. The specific hardware used to perform QKD can introduce vulnerabilities, resulting in several well-publicized attacks on commercial QKD systems.
[
127
]
- Quantum key distribution increases the risk of denial of service. The sensitivity to an eavesdropper as the theoretical basis for QKD security claims also shows that denial of service is a significant risk for QKD.
Quantum key distribution increases the risk of denial of service. The sensitivity to an eavesdropper as the theoretical basis for QKD security claims also shows that denial of service is a significant risk for QKD.
In response to problem 1 above, attempts to deliver authentication keys using post-quantum cryptography (or quantum-resistant cryptography) have been proposed worldwide. On the other hand, quantum-resistant cryptography is cryptography belonging to the class of computational security. In 2015, a research result was already published that "sufficient care must be taken in implementation to achieve information-theoretic security for the system as a whole when authentication keys that are not information-theoretic secure are used" (if the authentication key is not information-theoretically secure, an attacker can break it to bring all classical and quantum communications under control and relay them to launch aman-in-the-middle attack).[128]Ericsson, a private company, also cites and points out the above problems and then presents a report that it may not be able to support thezero trust security model, which is a recent trend in network security technology.[129]

In response to problem 1 above, attempts to deliver authentication keys using post-quantum cryptography (or quantum-resistant cryptography) have been proposed worldwide. On the other hand, quantum-resistant cryptography is cryptography belonging to the class of computational security. In 2015, a research result was already published that "sufficient care must be taken in implementation to achieve information-theoretic security for the system as a whole when authentication keys that are not information-theoretic secure are used" (if the authentication key is not information-theoretically secure, an attacker can break it to bring all classical and quantum communications under control and relay them to launch a
man-in-the-middle attack
).
[
128
]
Ericsson, a private company, also cites and points out the above problems and then presents a report that it may not be able to support the
zero trust security model
, which is a recent trend in network security technology.
[
129
]

### Quantum cryptography in education

Quantum cryptography in education
[
edit
]
Quantum cryptography, specifically the BB84 protocol, has become an important topic in physics and computer science education. The challenge of teaching quantum cryptography lies in the technical requirements and the conceptual complexity of quantum mechanics. However, simplified experimental setups for educational purposes are becoming more common,[130]allowing undergraduate students to engage with the core principles of quantum key distribution (QKD) without requiring advanced quantum technology.

Quantum cryptography, specifically the BB84 protocol, has become an important topic in physics and computer science education. The challenge of teaching quantum cryptography lies in the technical requirements and the conceptual complexity of quantum mechanics. However, simplified experimental setups for educational purposes are becoming more common,
[
130
]
allowing undergraduate students to engage with the core principles of quantum key distribution (QKD) without requiring advanced quantum technology.

## References

References
[
edit
]
- ↑Gisin, Nicolas; Ribordy, Grégoire; Tittel, Wolfgang; Zbinden, Hugo (2002)."Quantum cryptography".Reviews of Modern Physics.74(1):145–195.arXiv:quant-ph/0101098.Bibcode:2002RvMP...74..145G.doi:10.1103/RevModPhys.74.145.S2CID6979295.
↑
Gisin, Nicolas; Ribordy, Grégoire; Tittel, Wolfgang; Zbinden, Hugo (2002).
"Quantum cryptography"
.
Reviews of Modern Physics
.
74
(1):
145–
195.
arXiv
:
quant-ph/0101098
.
Bibcode
:
2002RvMP...74..145G
.
doi
:
10.1103/RevModPhys.74.145
.
S2CID
6979295
.
- 123Pirandola, S.; Andersen, U. L.; Banchi, L.; Berta, M.; Bunandar, D.; Colbeck, R.; Englund, D.; Gehring, T.; Lupo, C.; Ottaviani, C.; Pereira, J. L.; etal. (2020)."Advances in quantum cryptography".Advances in Optics and Photonics.12(4):1012–1236.arXiv:1906.01645.Bibcode:2020AdOP...12.1012P.doi:10.1364/AOP.361502.S2CID174799187.
1
2
3
Pirandola, S.; Andersen, U. L.; Banchi, L.; Berta, M.; Bunandar, D.; Colbeck, R.; Englund, D.; Gehring, T.; Lupo, C.; Ottaviani, C.; Pereira, J. L.; et
al. (2020).
"Advances in quantum cryptography"
.
Advances in Optics and Photonics
.
12
(4):
1012–
1236.
arXiv
:
1906.01645
.
Bibcode
:
2020AdOP...12.1012P
.
doi
:
10.1364/AOP.361502
.
S2CID
174799187
.
- ↑Renner, Renato; Wolf, Ramona (2023). "Quantum Advantage in Cryptography".AIAA Journal.61(5):1895–1910.arXiv:2206.04078.Bibcode:2023AIAAJ..61.1895R.doi:10.2514/1.J062267.ISSN0001-1452.
↑
Renner, Renato; Wolf, Ramona (2023). "Quantum Advantage in Cryptography".
AIAA Journal
.
61
(5):
1895–
1910.
arXiv
:
2206.04078
.
Bibcode
:
2023AIAAJ..61.1895R
.
doi
:
10.2514/1.J062267
.
ISSN
0001-1452
.
- ↑Gisin, Nicolas; Ribordy, Grégoire; Tittel, Wolfgang; Zbinden, Hugo (8 March 2002)."Quantum cryptography".Reviews of Modern Physics.74(1):145–195.arXiv:quant-ph/0101098.Bibcode:2002RvMP...74..145G.doi:10.1103/RevModPhys.74.145.
↑
Gisin, Nicolas; Ribordy, Grégoire; Tittel, Wolfgang; Zbinden, Hugo (8 March 2002).
"Quantum cryptography"
.
Reviews of Modern Physics
.
74
(1):
145–
195.
arXiv
:
quant-ph/0101098
.
Bibcode
:
2002RvMP...74..145G
.
doi
:
10.1103/RevModPhys.74.145
.
- ↑Nielsen, Michael A.; Chuang, Isaac L. (9 December 2010).Quantum Computation and Quantum Information: 10th Anniversary Edition.doi:10.1017/CBO9780511976667.ISBN978-1-107-00217-3. Retrieved2 September2025.
↑
Nielsen, Michael A.; Chuang, Isaac L. (9 December 2010).
Quantum Computation and Quantum Information: 10th Anniversary Edition
.
doi
:
10.1017/CBO9780511976667
.
ISBN
978-1-107-00217-3
. Retrieved
2 September
2025
.
- ↑Mitra, Saptarshi; Jana, Bappaditya; Bhattacharya, Supratim; Pal, Prashnatita; Poray, Jayanta (November 2017). "Quantum cryptography: Overview, security issues and future challenges".2017 4th International Conference on Opto-Electronics and Applied Optics (Optronix). pp.1–7.doi:10.1109/OPTRONIX.2017.8350006.ISBN978-1-5386-1119-7.
↑
Mitra, Saptarshi; Jana, Bappaditya; Bhattacharya, Supratim; Pal, Prashnatita; Poray, Jayanta (November 2017). "Quantum cryptography: Overview, security issues and future challenges".
2017 4th International Conference on Opto-Electronics and Applied Optics (Optronix)
. pp.
1–
7.
doi
:
10.1109/OPTRONIX.2017.8350006
.
ISBN
978-1-5386-1119-7
.
- 12Bennett, Charles H.; etal. (1992)."Experimental quantum cryptography".Journal of Cryptology.5(1):3–28.doi:10.1007/bf00191318.S2CID206771454.
1
2
Bennett, Charles H.; et
al. (1992).
"Experimental quantum cryptography"
.
Journal of Cryptology
.
5
(1):
3–
28.
doi
:
10.1007/bf00191318
.
S2CID
206771454
.
- ↑Wiesner, Stephen (1983). "Conjugate coding".ACM SIGACT News.15(1):78–88.doi:10.1145/1008908.1008920.S2CID207155055.
↑
Wiesner, Stephen (1983). "Conjugate coding".
ACM SIGACT News
.
15
(1):
78–
88.
doi
:
10.1145/1008908.1008920
.
S2CID
207155055
.
- ↑Bennett, C. H.; Brassard, G. (1984). "Quantum cryptography: Public key distribution and coin tossing".Proceedings of the International Conference on Computers, Systems & Signal Processing, Bangalore, India. Vol.1. New York: IEEE. pp.175–179.Reprinted asBennett, C. H.; Brassard, G. (4 December 2014)."Quantum cryptography: Public key distribution and coin tossing".Theoretical Computer Science. Theoretical Aspects of Quantum Cryptography – celebrating 30 years of BB84.560(1):7–11.arXiv:2003.06557.Bibcode:2014TComS.560....7B.doi:10.1016/j.tcs.2014.05.025.
↑
Bennett, C. H.; Brassard, G. (1984). "Quantum cryptography: Public key distribution and coin tossing".
Proceedings of the International Conference on Computers, Systems & Signal Processing, Bangalore, India
. Vol.
1. New York: IEEE. pp.
175–
179.
Reprinted as
Bennett, C. H.; Brassard, G. (4 December 2014).
"Quantum cryptography: Public key distribution and coin tossing"
.
Theoretical Computer Science
. Theoretical Aspects of Quantum Cryptography – celebrating 30 years of BB84.
560
(1):
7–
11.
arXiv
:
2003.06557
.
Bibcode
:
2014TComS.560....7B
.
doi
:
10.1016/j.tcs.2014.05.025
.
- ↑"What Is Quantum Cryptography? | IBM".www.ibm.com. 29 November 2023. Retrieved25 September2024.
↑
"What Is Quantum Cryptography? | IBM"
.
www.ibm.com
. 29 November 2023
. Retrieved
25 September
2024
.
- ↑Ekert, A (1991). "Quantum cryptography based on Bell's theorem".Physical Review Letters.67(6):661–663.Bibcode:1991PhRvL..67..661E.doi:10.1103/physrevlett.67.661.PMID10044956.S2CID27683254.
↑
Ekert, A (1991). "Quantum cryptography based on Bell's theorem".
Physical Review Letters
.
67
(6):
661–
663.
Bibcode
:
1991PhRvL..67..661E
.
doi
:
10.1103/physrevlett.67.661
.
PMID
10044956
.
S2CID
27683254
.
- ↑"Crypto-gram: December 15, 2003 – Schneier on Security".www.schneier.com. Retrieved13 October2020.
↑
"Crypto-gram: December 15, 2003 – Schneier on Security"
.
www.schneier.com
. Retrieved
13 October
2020
.
- 12345Stebila, Douglas; Mosca, Michele; Lütkenhaus, Norbert (2010)."The Case for Quantum Key Distribution". In Sergienko, Alexander; Pascazio, Saverio; Villoresi, Paolo (eds.).Quantum Communication and Quantum Networking. Vol.36. Berlin, Heidelberg: Springer Berlin Heidelberg. pp.283–296.arXiv:0902.2839.Bibcode:2010qcqn.book..283S.doi:10.1007/978-3-642-11731-2_35.ISBN978-3-642-11730-5.S2CID457259. Retrieved13 October2020.
1
2
3
4
5
Stebila, Douglas; Mosca, Michele; Lütkenhaus, Norbert (2010).
"The Case for Quantum Key Distribution"
. In Sergienko, Alexander; Pascazio, Saverio; Villoresi, Paolo (eds.).
Quantum Communication and Quantum Networking
. Vol.
36. Berlin, Heidelberg: Springer Berlin Heidelberg. pp.
283–
296.
arXiv
:
0902.2839
.
Bibcode
:
2010qcqn.book..283S
.
doi
:
10.1007/978-3-642-11731-2_35
.
ISBN
978-3-642-11730-5
.
S2CID
457259
. Retrieved
13 October
2020
.
- ↑"FastStats".www.cdc.gov. 4 August 2020. Retrieved13 October2020.
↑
"FastStats"
.
www.cdc.gov
. 4 August 2020
. Retrieved
13 October
2020
.
- ↑Rights (OCR), Office for Civil (7 May 2008)."Privacy".HHS.gov. Retrieved13 October2020.
↑
Rights (OCR), Office for Civil (7 May 2008).
"Privacy"
.
HHS.gov
. Retrieved
13 October
2020
.
- 12Lo, Hoi-Kwong; Chau, H. F. (1999)."Unconditional Security of Quantum Key Distribution over Arbitrarily Long Distances"(PDF).Science.283(5410):2050–2056.arXiv:quant-ph/9803006.Bibcode:1999Sci...283.2050L.doi:10.1126/science.283.5410.2050.JSTOR2896688.PMID10092221.S2CID2948183.
1
2
Lo, Hoi-Kwong; Chau, H. F. (1999).
"Unconditional Security of Quantum Key Distribution over Arbitrarily Long Distances"
(PDF)
.
Science
.
283
(5410):
2050–
2056.
arXiv
:
quant-ph/9803006
.
Bibcode
:
1999Sci...283.2050L
.
doi
:
10.1126/science.283.5410.2050
.
JSTOR
2896688
.
PMID
10092221
.
S2CID
2948183
.
- ↑Pirandola, S.; García-Patrón, R.; Braunstein, S. L.; Lloyd, S. (2009). "Direct and Reverse Secret-Key Capacities of a Quantum Channel".Physical Review Letters.102(5) 050503.arXiv:0809.3273.Bibcode:2009PhRvL.102e0503P.doi:10.1103/PhysRevLett.102.050503.PMID19257494.S2CID665165.
↑
Pirandola, S.; García-Patrón, R.; Braunstein, S. L.; Lloyd, S. (2009). "Direct and Reverse Secret-Key Capacities of a Quantum Channel".
Physical Review Letters
.
102
(5) 050503.
arXiv
:
0809.3273
.
Bibcode
:
2009PhRvL.102e0503P
.
doi
:
10.1103/PhysRevLett.102.050503
.
PMID
19257494
.
S2CID
665165
.
- ↑Takeoka, Masahiro; Guha, Saikat; Wilde, Mark M. (2014). "Fundamental rate-loss tradeoff for optical quantum key distribution".Nature Communications.55235.arXiv:1504.06390.Bibcode:2014NatCo...5.5235T.doi:10.1038/ncomms6235.PMID25341406.S2CID20580923.
↑
Takeoka, Masahiro; Guha, Saikat; Wilde, Mark M. (2014). "Fundamental rate-loss tradeoff for optical quantum key distribution".
Nature Communications
.
5
5235.
arXiv
:
1504.06390
.
Bibcode
:
2014NatCo...5.5235T
.
doi
:
10.1038/ncomms6235
.
PMID
25341406
.
S2CID
20580923
.
- 12Pirandola, S.; Laurenza, R.; Ottaviani, C.; Banchi, L. (2017)."Fundamental limits of repeaterless quantum communications".Nature Communications.815043.arXiv:1510.08863.Bibcode:2017NatCo...815043P.doi:10.1038/ncomms15043.PMC5414096.PMID28443624.
1
2
Pirandola, S.; Laurenza, R.; Ottaviani, C.; Banchi, L. (2017).
"Fundamental limits of repeaterless quantum communications"
.
Nature Communications
.
8
15043.
arXiv
:
1510.08863
.
Bibcode
:
2017NatCo...815043P
.
doi
:
10.1038/ncomms15043
.
PMC
5414096
.
PMID
28443624
.
- 12Shields, A. J.; Dynes, J. F.; Yuan, Z. L.; Lucamarini, M. (May 2018). "Overcoming the rate–distance limit of quantum key distribution without quantum repeaters".Nature.557(7705):400–403.arXiv:1811.06826.Bibcode:2018Natur.557..400L.doi:10.1038/s41586-018-0066-6.ISSN1476-4687.PMID29720656.S2CID21698666.
1
2
Shields, A. J.; Dynes, J. F.; Yuan, Z. L.; Lucamarini, M. (May 2018). "Overcoming the rate–distance limit of quantum key distribution without quantum repeaters".
Nature
.
557
(7705):
400–
403.
arXiv
:
1811.06826
.
Bibcode
:
2018Natur.557..400L
.
doi
:
10.1038/s41586-018-0066-6
.
ISSN
1476-4687
.
PMID
29720656
.
S2CID
21698666
.
- ↑Pirandola, S. (2019). "End-to-end capacities of a quantum communication network".Communications Physics.2(1) 51.arXiv:1601.00966.Bibcode:2019CmPhy...2...51P.doi:10.1038/s42005-019-0147-3.S2CID170078611.
↑
Pirandola, S. (2019). "End-to-end capacities of a quantum communication network".
Communications Physics
.
2
(1) 51.
arXiv
:
1601.00966
.
Bibcode
:
2019CmPhy...2...51P
.
doi
:
10.1038/s42005-019-0147-3
.
S2CID
170078611
.
- ↑Minder, Mariella; Pittaluga, Mirko; Roberts, George; Lucamarini, Marco; Dynes, James F.; Yuan, Zhiliang; Shields, Andrew J. (February 2019). "Experimental quantum key distribution beyond the repeaterless secret key capacity".Nature Photonics.13(5):334–338.arXiv:1910.01951.Bibcode:2019NaPho..13..334M.doi:10.1038/s41566-019-0377-7.S2CID126717712.
↑
Minder, Mariella; Pittaluga, Mirko; Roberts, George; Lucamarini, Marco; Dynes, James F.; Yuan, Zhiliang; Shields, Andrew J. (February 2019). "Experimental quantum key distribution beyond the repeaterless secret key capacity".
Nature Photonics
.
13
(5):
334–
338.
arXiv
:
1910.01951
.
Bibcode
:
2019NaPho..13..334M
.
doi
:
10.1038/s41566-019-0377-7
.
S2CID
126717712
.
- ↑Wang, Xiang-Bin; Yu, Zong-Wen; Hu, Xiao-Long (2018). "Twin-field quantum key distribution with large misalignment error".Physical Review A.98(6) 062323.arXiv:1805.09222.Bibcode:2018PhRvA..98f2323W.doi:10.1103/PhysRevA.98.062323.S2CID51204011.
↑
Wang, Xiang-Bin; Yu, Zong-Wen; Hu, Xiao-Long (2018). "Twin-field quantum key distribution with large misalignment error".
Physical Review A
.
98
(6) 062323.
arXiv
:
1805.09222
.
Bibcode
:
2018PhRvA..98f2323W
.
doi
:
10.1103/PhysRevA.98.062323
.
S2CID
51204011
.
- ↑Xu, Hai; Yu, Zong-Wen; Hu, Xiao-Long; Wang, Xiang-Bin (2020). "Improved results for sending-or-not-sending twin-field quantun key distribution: breaking the absolute limit of repeaterless key rate".Physical Review A.101042330.arXiv:1904.06331.doi:10.1103/PhysRevA.101.042330.S2CID219003338.
↑
Xu, Hai; Yu, Zong-Wen; Hu, Xiao-Long; Wang, Xiang-Bin (2020). "Improved results for sending-or-not-sending twin-field quantun key distribution: breaking the absolute limit of repeaterless key rate".
Physical Review A
.
101
042330.
arXiv
:
1904.06331
.
doi
:
10.1103/PhysRevA.101.042330
.
S2CID
219003338
.
- ↑Cui, C.; Yin, A.-Q.; Wang, R.; Chen, W.; Wang, S.; Guo, G.-C.; Han, Z.-F. (2019). "Twin-Field Quantum Key Distribution without Phase Postselection".Physical Review Applied.11(3) 034053.arXiv:1807.02334.Bibcode:2019PhRvP..11c4053C.doi:10.1103/PhysRevApplied.11.034053.S2CID53624575.
↑
Cui, C.; Yin, A.-Q.; Wang, R.; Chen, W.; Wang, S.; Guo, G.-C.; Han, Z.-F. (2019). "Twin-Field Quantum Key Distribution without Phase Postselection".
Physical Review Applied
.
11
(3) 034053.
arXiv
:
1807.02334
.
Bibcode
:
2019PhRvP..11c4053C
.
doi
:
10.1103/PhysRevApplied.11.034053
.
S2CID
53624575
.
- 123Mayers, Dominic (1997). "Unconditionally Secure Quantum Bit Commitment is Impossible".Physical Review Letters.78(17):3414–3417.arXiv:quant-ph/9605044.Bibcode:1997PhRvL..78.3414M.CiteSeerX10.1.1.251.5550.doi:10.1103/PhysRevLett.78.3414.S2CID14522232.
1
2
3
Mayers, Dominic (1997). "Unconditionally Secure Quantum Bit Commitment is Impossible".
Physical Review Letters
.
78
(17):
3414–
3417.
arXiv
:
quant-ph/9605044
.
Bibcode
:
1997PhRvL..78.3414M
.
CiteSeerX
10.1.1.251.5550
.
doi
:
10.1103/PhysRevLett.78.3414
.
S2CID
14522232
.
- ↑Lo, H.-K.; Chau, H. (1997). "Is Quantum Bit Commitment Really Possible?".Physical Review Letters.78(17): 3410.arXiv:quant-ph/9603004.Bibcode:1997PhRvL..78.3410L.doi:10.1103/PhysRevLett.78.3410.S2CID3264257.
↑
Lo, H.-K.; Chau, H. (1997). "Is Quantum Bit Commitment Really Possible?".
Physical Review Letters
.
78
(17): 3410.
arXiv
:
quant-ph/9603004
.
Bibcode
:
1997PhRvL..78.3410L
.
doi
:
10.1103/PhysRevLett.78.3410
.
S2CID
3264257
.
- ↑Lo, H.-K.; Chau, H. (1998). "Why quantum bit commitment and ideal quantum coin tossing are impossible".Physica D: Nonlinear Phenomena.120(1–2):177–187.arXiv:quant-ph/9711065.Bibcode:1998PhyD..120..177L.doi:10.1016/S0167-2789(98)00053-0.S2CID14378275.
↑
Lo, H.-K.; Chau, H. (1998). "Why quantum bit commitment and ideal quantum coin tossing are impossible".
Physica D: Nonlinear Phenomena
.
120
(
1–
2):
177–
187.
arXiv
:
quant-ph/9711065
.
Bibcode
:
1998PhyD..120..177L
.
doi
:
10.1016/S0167-2789(98)00053-0
.
S2CID
14378275
.
- ↑Lo, H.-K. (1997). "Insecurity of quantum secure computations".Physical Review A.56(2):1154–1162.arXiv:quant-ph/9611031.Bibcode:1997PhRvA..56.1154L.doi:10.1103/PhysRevA.56.1154.S2CID17813922.
↑
Lo, H.-K. (1997). "Insecurity of quantum secure computations".
Physical Review A
.
56
(2):
1154–
1162.
arXiv
:
quant-ph/9611031
.
Bibcode
:
1997PhRvA..56.1154L
.
doi
:
10.1103/PhysRevA.56.1154
.
S2CID
17813922
.
- ↑Kent, A. (1999). "Unconditionally Secure Bit Commitment".Physical Review Letters.83(7):1447–1450.arXiv:quant-ph/9810068.Bibcode:1999PhRvL..83.1447K.doi:10.1103/PhysRevLett.83.1447.S2CID8823466.
↑
Kent, A. (1999). "Unconditionally Secure Bit Commitment".
Physical Review Letters
.
83
(7):
1447–
1450.
arXiv
:
quant-ph/9810068
.
Bibcode
:
1999PhRvL..83.1447K
.
doi
:
10.1103/PhysRevLett.83.1447
.
S2CID
8823466
.
- ↑Kent, A. (1999). "Coin Tossing is Strictly Weaker than Bit Commitment".Physical Review Letters.83(25):5382–5384.arXiv:quant-ph/9810067.Bibcode:1999PhRvL..83.5382K.doi:10.1103/PhysRevLett.83.5382.S2CID16764407.
↑
Kent, A. (1999). "Coin Tossing is Strictly Weaker than Bit Commitment".
Physical Review Letters
.
83
(25):
5382–
5384.
arXiv
:
quant-ph/9810067
.
Bibcode
:
1999PhRvL..83.5382K
.
doi
:
10.1103/PhysRevLett.83.5382
.
S2CID
16764407
.
- 12Dambort, Stuart Mason (26 March 2014)."Heads or tails: Experimental quantum coin flipping cryptography performs better than classical protocols".Phys.org.Archivedfrom the original on 25 March 2017.
1
2
Dambort, Stuart Mason (26 March 2014).
"Heads or tails: Experimental quantum coin flipping cryptography performs better than classical protocols"
.
Phys.org
.
Archived
from the original on 25 March 2017.
- ↑Doescher, C.; Keyl, M. (2002). "An introduction to quantum coin-tossing".arXiv:quant-ph/0206088.
↑
Doescher, C.; Keyl, M. (2002). "An introduction to quantum coin-tossing".
arXiv
:
quant-ph/0206088
.
- ↑Pappa, Anna; Jouguet, Paul; Lawson, Thomas; Chailloux, André; Legré, Matthieu; Trinkler, Patrick; Kerenidis, Iordanis; Diamanti, Eleni (24 April 2014)."Experimental plug and play quantum coin flipping".Nature Communications.5(1): 3717.arXiv:1306.3368.Bibcode:2014NatCo...5.3717P.doi:10.1038/ncomms4717.ISSN2041-1723.PMID24758868.S2CID205325088.
↑
Pappa, Anna; Jouguet, Paul; Lawson, Thomas; Chailloux, André; Legré, Matthieu; Trinkler, Patrick; Kerenidis, Iordanis; Diamanti, Eleni (24 April 2014).
"Experimental plug and play quantum coin flipping"
.
Nature Communications
.
5
(1): 3717.
arXiv
:
1306.3368
.
Bibcode
:
2014NatCo...5.3717P
.
doi
:
10.1038/ncomms4717
.
ISSN
2041-1723
.
PMID
24758868
.
S2CID
205325088
.
- ↑Ambainis, Andris (1 March 2004)."A new protocol and lower bounds for quantum coin flipping".Journal of Computer and System Sciences.68(2):398–416.arXiv:quant-ph/0204022.doi:10.1016/j.jcss.2003.07.010.ISSN0022-0000.
↑
Ambainis, Andris (1 March 2004).
"A new protocol and lower bounds for quantum coin flipping"
.
Journal of Computer and System Sciences
.
68
(2):
398–
416.
arXiv
:
quant-ph/0204022
.
doi
:
10.1016/j.jcss.2003.07.010
.
ISSN
0022-0000
.
- 1234Bennett, Charles H.; Brassard, Gilles (4 December 2014)."Quantum cryptography: Public key distribution and coin tossing".Theoretical Computer Science.560:7–11.arXiv:2003.06557.Bibcode:2014TComS.560....7B.doi:10.1016/j.tcs.2014.05.025.ISSN0304-3975.S2CID27022972.
1
2
3
4
Bennett, Charles H.; Brassard, Gilles (4 December 2014).
"Quantum cryptography: Public key distribution and coin tossing"
.
Theoretical Computer Science
.
560
:
7–
11.
arXiv
:
2003.06557
.
Bibcode
:
2014TComS.560....7B
.
doi
:
10.1016/j.tcs.2014.05.025
.
ISSN
0304-3975
.
S2CID
27022972
.
- 12Crépeau, Claude; Joe, Kilian (1988).Achieving Oblivious Transfer Using Weakened Security Assumptions (Extended Abstract). FOCS 1988. IEEE. pp.42–52.
1
2
Crépeau, Claude; Joe, Kilian (1988).
Achieving Oblivious Transfer Using Weakened Security Assumptions (Extended Abstract)
. FOCS 1988. IEEE. pp.
42–
52.
- 12Kilian, Joe (1988).Founding cryptography on oblivious transfer. STOC 1988. ACM. pp.20–31. Archived fromthe originalon 24 December 2004.
1
2
Kilian, Joe (1988).
Founding cryptography on oblivious transfer
. STOC 1988. ACM. pp.
20–
31. Archived from
the original
on 24 December 2004.
- ↑Brassard, Gilles; Claude, Crépeau; Jozsa, Richard; Langlois, Denis (1993).A Quantum Bit Commitment Scheme Provably Unbreakable by both Parties. FOCS 1993. IEEE. pp.362–371.
↑
Brassard, Gilles; Claude, Crépeau; Jozsa, Richard; Langlois, Denis (1993).
A Quantum Bit Commitment Scheme Provably Unbreakable by both Parties
. FOCS 1993. IEEE. pp.
362–
371.
- ↑Lunghi, T.; Kaniewski, J.; Bussières, F.; Houlmann, R.; Tomamichel, M.; Kent, A.; Gisin, N.; Wehner, S.; Zbinden, H. (2013). "Experimental Bit Commitment Based on Quantum Communication and Special Relativity".Physical Review Letters.111(18) 180504.arXiv:1306.4801.Bibcode:2013PhRvL.111r0504L.doi:10.1103/PhysRevLett.111.180504.PMID24237497.S2CID15916727.
↑
Lunghi, T.; Kaniewski, J.; Bussières, F.; Houlmann, R.; Tomamichel, M.; Kent, A.; Gisin, N.; Wehner, S.; Zbinden, H. (2013). "Experimental Bit Commitment Based on Quantum Communication and Special Relativity".
Physical Review Letters
.
111
(18) 180504.
arXiv
:
1306.4801
.
Bibcode
:
2013PhRvL.111r0504L
.
doi
:
10.1103/PhysRevLett.111.180504
.
PMID
24237497
.
S2CID
15916727
.
- ↑Wang, Ming-Qiang; Wang, Xue; Zhan, Tao (2018). "Unconditionally secure multi-party quantum commitment scheme".Quantum Information Processing.17(2): 31.Bibcode:2018QuIP...17...31W.doi:10.1007/s11128-017-1804-7.ISSN1570-0755.S2CID3603337.
↑
Wang, Ming-Qiang; Wang, Xue; Zhan, Tao (2018). "Unconditionally secure multi-party quantum commitment scheme".
Quantum Information Processing
.
17
(2): 31.
Bibcode
:
2018QuIP...17...31W
.
doi
:
10.1007/s11128-017-1804-7
.
ISSN
1570-0755
.
S2CID
3603337
.
- ↑Nikolopoulos, Georgios M. (2019). "Optical scheme for cryptographic commitments with physical unclonable keys".Optics Express.27(20):29367–29379.arXiv:1909.13094.Bibcode:2019OExpr..2729367N.doi:10.1364/OE.27.029367.PMID31684673.S2CID203593129.
↑
Nikolopoulos, Georgios M. (2019). "Optical scheme for cryptographic commitments with physical unclonable keys".
Optics Express
.
27
(20):
29367–
29379.
arXiv
:
1909.13094
.
Bibcode
:
2019OExpr..2729367N
.
doi
:
10.1364/OE.27.029367
.
PMID
31684673
.
S2CID
203593129
.
- 12Damgård, Ivan; Fehr, Serge; Salvail, Louis; Schaffner, Christian (2005).Cryptography in the Bounded Quantum-Storage Model. FOCS 2005. IEEE. pp.449–458.arXiv:quant-ph/0508222.
1
2
Damgård, Ivan; Fehr, Serge; Salvail, Louis; Schaffner, Christian (2005).
Cryptography in the Bounded Quantum-Storage Model
. FOCS 2005. IEEE. pp.
449–
458.
arXiv
:
quant-ph/0508222
.
- ↑Wehner, Stephanie; Schaffner, Christian; Terhal, Barbara M. (2008). "Cryptography from Noisy Storage".Physical Review Letters.100(22) 220502.arXiv:0711.2895.Bibcode:2008PhRvL.100v0502W.doi:10.1103/PhysRevLett.100.220502.PMID18643410.S2CID2974264.
↑
Wehner, Stephanie; Schaffner, Christian; Terhal, Barbara M. (2008). "Cryptography from Noisy Storage".
Physical Review Letters
.
100
(22) 220502.
arXiv
:
0711.2895
.
Bibcode
:
2008PhRvL.100v0502W
.
doi
:
10.1103/PhysRevLett.100.220502
.
PMID
18643410
.
S2CID
2974264
.
- ↑Doescher, C.; Keyl, M.; Wullschleger, Jürg (2009). "Unconditional security from noisy quantum storage".IEEE Transactions on Information Theory.58(3):1962–1984.arXiv:0906.1030.doi:10.1109/TIT.2011.2177772.S2CID12500084.
↑
Doescher, C.; Keyl, M.; Wullschleger, Jürg (2009). "Unconditional security from noisy quantum storage".
IEEE Transactions on Information Theory
.
58
(3):
1962–
1984.
arXiv
:
0906.1030
.
doi
:
10.1109/TIT.2011.2177772
.
S2CID
12500084
.
- ↑Cachin, Christian; Crépeau, Claude; Marcil, Julien (1998).Oblivious Transfer with a Memory-Bounded Receiver. FOCS 1998. IEEE. pp.493–502.
↑
Cachin, Christian; Crépeau, Claude; Marcil, Julien (1998).
Oblivious Transfer with a Memory-Bounded Receiver
. FOCS 1998. IEEE. pp.
493–
502.
- ↑Dziembowski, Stefan; Ueli, Maurer (2004).On Generating the Initial Key in the Bounded-Storage Model(PDF). Eurocrypt 2004. LNCS. Vol.3027. Springer. pp.126–137.Archived(PDF)from the original on 11 March 2020. Retrieved11 March2020.
↑
Dziembowski, Stefan; Ueli, Maurer (2004).
On Generating the Initial Key in the Bounded-Storage Model
(PDF)
. Eurocrypt 2004. LNCS. Vol.
3027. Springer. pp.
126–
137.
Archived
(PDF)
from the original on 11 March 2020
. Retrieved
11 March
2020
.
- ↑Chandran, Nishanth; Moriarty, Ryan; Goyal, Vipul; Ostrovsky, Rafail (2009)."Position-Based Cryptography".Cryptology ePrint Archive.
↑
Chandran, Nishanth; Moriarty, Ryan; Goyal, Vipul; Ostrovsky, Rafail (2009).
"Position-Based Cryptography"
.
Cryptology ePrint Archive
.
- ↑US 7075438,issued 11 July 2006
↑
US 7075438
,
issued 11 July 2006
- ↑Malaney, Robert (2010). "Location-dependent communications using quantum entanglement".Physical Review A.81(4) 042319.arXiv:1003.0949.Bibcode:2010PhRvA..81d2319M.doi:10.1103/PhysRevA.81.042319.S2CID118704298.
↑
Malaney, Robert (2010). "Location-dependent communications using quantum entanglement".
Physical Review A
.
81
(4) 042319.
arXiv
:
1003.0949
.
Bibcode
:
2010PhRvA..81d2319M
.
doi
:
10.1103/PhysRevA.81.042319
.
S2CID
118704298
.
- ↑Malaney, Robert (2010). "Quantum Location Verification in Noisy Channels".2010 IEEE Global Telecommunications Conference GLOBECOM 2010. IEEE Global Telecommunications Conference GLOBECOM 2010. pp.1–6.arXiv:1004.4689.doi:10.1109/GLOCOM.2010.5684009.ISBN978-1-4244-5636-9.
↑
Malaney, Robert (2010). "Quantum Location Verification in Noisy Channels".
2010 IEEE Global Telecommunications Conference GLOBECOM 2010
. IEEE Global Telecommunications Conference GLOBECOM 2010. pp.
1–
6.
arXiv
:
1004.4689
.
doi
:
10.1109/GLOCOM.2010.5684009
.
ISBN
978-1-4244-5636-9
.
- ↑Doescher, C.; Keyl, M.; Spiller, Timothy P. (2011). "Quantum Tagging: Authenticating Location via Quantum Information and Relativistic Signalling Constraints".Physical Review A.84(1) 012326.arXiv:1008.2147.Bibcode:2011PhRvA..84a2326K.doi:10.1103/PhysRevA.84.012326.S2CID1042757.
↑
Doescher, C.; Keyl, M.; Spiller, Timothy P. (2011). "Quantum Tagging: Authenticating Location via Quantum Information and Relativistic Signalling Constraints".
Physical Review A
.
84
(1) 012326.
arXiv
:
1008.2147
.
Bibcode
:
2011PhRvA..84a2326K
.
doi
:
10.1103/PhysRevA.84.012326
.
S2CID
1042757
.
- ↑Lau, Hoi-Kwan; Lo, Hoi-Kwong (2010). "Insecurity of position-based quantum-cryptography protocols against entanglement attacks".Physical Review A.83(1) 012322.arXiv:1009.2256.Bibcode:2011PhRvA..83a2322L.doi:10.1103/PhysRevA.83.012322.S2CID17022643.
↑
Lau, Hoi-Kwan; Lo, Hoi-Kwong (2010). "Insecurity of position-based quantum-cryptography protocols against entanglement attacks".
Physical Review A
.
83
(1) 012322.
arXiv
:
1009.2256
.
Bibcode
:
2011PhRvA..83a2322L
.
doi
:
10.1103/PhysRevA.83.012322
.
S2CID
17022643
.
- ↑Doescher, C.; Keyl, M.; Fehr, Serge; Gelles, Ran; Goyal, Vipul; Ostrovsky, Rafail; Schaffner, Christian (2010). "Position-Based Quantum Cryptography: Impossibility and Constructions".SIAM Journal on Computing.43:150–178.arXiv:1009.2490.Bibcode:2010arXiv1009.2490B.doi:10.1137/130913687.S2CID220613220.
↑
Doescher, C.; Keyl, M.; Fehr, Serge; Gelles, Ran; Goyal, Vipul; Ostrovsky, Rafail; Schaffner, Christian (2010). "Position-Based Quantum Cryptography: Impossibility and Constructions".
SIAM Journal on Computing
.
43
:
150–
178.
arXiv
:
1009.2490
.
Bibcode
:
2010arXiv1009.2490B
.
doi
:
10.1137/130913687
.
S2CID
220613220
.
- ↑Beigi, Salman; König, Robert (2011). "Simplified instantaneous non-local quantum computation with applications to position-based cryptography".New Journal of Physics.13(9) 093036.arXiv:1101.1065.Bibcode:2011NJPh...13i3036B.doi:10.1088/1367-2630/13/9/093036.S2CID27648088.
↑
Beigi, Salman; König, Robert (2011). "Simplified instantaneous non-local quantum computation with applications to position-based cryptography".
New Journal of Physics
.
13
(9) 093036.
arXiv
:
1101.1065
.
Bibcode
:
2011NJPh...13i3036B
.
doi
:
10.1088/1367-2630/13/9/093036
.
S2CID
27648088
.
- ↑Malaney, Robert (2016). "The Quantum Car".IEEE Wireless Communications Letters.5(6):624–627.arXiv:1512.03521.Bibcode:2016IWCL....5..624M.doi:10.1109/LWC.2016.2607740.S2CID2483729.
↑
Malaney, Robert (2016). "The Quantum Car".
IEEE Wireless Communications Letters
.
5
(6):
624–
627.
arXiv
:
1512.03521
.
Bibcode
:
2016IWCL....5..624M
.
doi
:
10.1109/LWC.2016.2607740
.
S2CID
2483729
.
- ↑Radanliev, Petar (October 2023)."Red Teaming Generative AI/NLP, the BB84 quantum cryptography protocol and the NIST-approved Quantum-Resistant Cryptographic Algorithms".University of Oxford.arXiv:2310.04425.
↑
Radanliev, Petar (October 2023).
"Red Teaming Generative AI/NLP, the BB84 quantum cryptography protocol and the NIST-approved Quantum-Resistant Cryptographic Algorithms"
.
University of Oxford
.
arXiv
:
2310.04425
.
- ↑Mayers, Dominic; Yao, Andrew C.-C. (1998).Quantum Cryptography with Imperfect Apparatus. IEEE Symposium on Foundations of Computer Science (FOCS).arXiv:quant-ph/9809039.Bibcode:1998quant.ph..9039M.
↑
Mayers, Dominic; Yao, Andrew C.-C. (1998).
Quantum Cryptography with Imperfect Apparatus
. IEEE Symposium on Foundations of Computer Science (FOCS).
arXiv
:
quant-ph/9809039
.
Bibcode
:
1998quant.ph..9039M
.
- ↑Colbeck, Roger (December 2006). "Chapter 5".Quantum And Relativistic Protocols For Secure Multi-Party Computation(Thesis). University of Cambridge.arXiv:0911.3814.
↑
Colbeck, Roger (December 2006). "Chapter 5".
Quantum And Relativistic Protocols For Secure Multi-Party Computation
(Thesis). University of Cambridge.
arXiv
:
0911.3814
.
- ↑Vazirani, Umesh; Vidick, Thomas (2014). "Fully Device-Independent Quantum Key Distribution".Physical Review Letters.113(2): 140501.arXiv:1403.3830.Bibcode:2014PhRvL.113b0501A.doi:10.1103/PhysRevLett.113.020501.PMID25062151.S2CID23057977.
↑
Vazirani, Umesh; Vidick, Thomas (2014). "Fully Device-Independent Quantum Key Distribution".
Physical Review Letters
.
113
(2): 140501.
arXiv
:
1403.3830
.
Bibcode
:
2014PhRvL.113b0501A
.
doi
:
10.1103/PhysRevLett.113.020501
.
PMID
25062151
.
S2CID
23057977
.
- 12Miller, Carl; Shi, Yaoyun (2014). "Robust protocols for securely expanding randomness and distributing keys using untrusted quantum devices".Journal of the ACM.63(4): 33.arXiv:1402.0489.Bibcode:2014arXiv1402.0489M.
1
2
Miller, Carl; Shi, Yaoyun (2014). "Robust protocols for securely expanding randomness and distributing keys using untrusted quantum devices".
Journal of the ACM
.
63
(4): 33.
arXiv
:
1402.0489
.
Bibcode
:
2014arXiv1402.0489M
.
- ↑Miller, Carl; Shi, Yaoyun (2017). "Universal security for randomness expansion".SIAM Journal on Computing.46(4):1304–1335.arXiv:1411.6608.doi:10.1137/15M1044333.S2CID6792482.
↑
Miller, Carl; Shi, Yaoyun (2017). "Universal security for randomness expansion".
SIAM Journal on Computing
.
46
(4):
1304–
1335.
arXiv
:
1411.6608
.
doi
:
10.1137/15M1044333
.
S2CID
6792482
.
- ↑Chung, Kai-Min; Shi, Yaoyun; Wu, Xiaodi (2014). "Physical Randomness Extractors: Generating Random Numbers with Minimal Assumptions".arXiv:1402.4797[quant-ph].
↑
Chung, Kai-Min; Shi, Yaoyun; Wu, Xiaodi (2014). "Physical Randomness Extractors: Generating Random Numbers with Minimal Assumptions".
arXiv
:
1402.4797
[
quant-ph
].
- ↑Arnon-Friedman, Rotem; Dupuis, Frédéric; Fawzi, Omar;Renner, Renato; Vidick, Thomas (31 January 2018)."Practical device-independent quantum cryptography via entropy accumulation".Nature Communications.9(1): 459.Bibcode:2018NatCo...9..459A.doi:10.1038/s41467-017-02307-4.ISSN2041-1723.PMC5792631.PMID29386507.
↑
Arnon-Friedman, Rotem; Dupuis, Frédéric; Fawzi, Omar;
Renner, Renato
; Vidick, Thomas (31 January 2018).
"Practical device-independent quantum cryptography via entropy accumulation"
.
Nature Communications
.
9
(1): 459.
Bibcode
:
2018NatCo...9..459A
.
doi
:
10.1038/s41467-017-02307-4
.
ISSN
2041-1723
.
PMC
5792631
.
PMID
29386507
.
- ↑Daniel J. Bernstein(2009)."Introduction to post-quantum cryptography"(PDF).Post-Quantum Cryptography.
↑
Daniel J. Bernstein
(2009).
"Introduction to post-quantum cryptography"
(PDF)
.
Post-Quantum Cryptography
.
- ↑Daniel J. Bernstein(17 May 2009).Cost analysis of hash collisions: Will quantum computers make SHARCS obsolete?(PDF)(Report).Archived(PDF)from the original on 25 August 2017.
↑
Daniel J. Bernstein
(17 May 2009).
Cost analysis of hash collisions: Will quantum computers make SHARCS obsolete?
(PDF)
(Report).
Archived
(PDF)
from the original on 25 August 2017.
- ↑"Post-quantum cryptography".Archivedfrom the original on 17 July 2011. Retrieved29 August2010.
↑
"Post-quantum cryptography"
.
Archived
from the original on 17 July 2011
. Retrieved
29 August
2010
.
- ↑Bernstein, Daniel J.; Buchmann, Johannes; Dahmen, Erik, eds. (2009).Post-quantum cryptography. Springer.ISBN978-3-540-88701-0.
↑
Bernstein, Daniel J.; Buchmann, Johannes; Dahmen, Erik, eds. (2009).
Post-quantum cryptography
. Springer.
ISBN
978-3-540-88701-0
.
- ↑Watrous, John(2009). "Zero-Knowledge against Quantum Attacks".SIAM Journal on Computing.39(1):25–58.arXiv:quant-ph/0511020.CiteSeerX10.1.1.190.2789.doi:10.1137/060670997.
↑
Watrous, John
(2009). "Zero-Knowledge against Quantum Attacks".
SIAM Journal on Computing
.
39
(1):
25–
58.
arXiv
:
quant-ph/0511020
.
CiteSeerX
10.1.1.190.2789
.
doi
:
10.1137/060670997
.
- ↑"NSA Suite B Cryptography". Archived fromthe originalon 1 January 2016. Retrieved29 December2015.
↑
"NSA Suite B Cryptography"
. Archived from
the original
on 1 January 2016
. Retrieved
29 December
2015
.
- ↑"Quantum Resistant Public Key Exchange: The Supersingular Isogenous Diffie-Hellman Protocol – CoinFabrik Blog".blog.coinfabrik.com. 13 October 2016.Archivedfrom the original on 2 February 2017. Retrieved24 January2017.
↑
"Quantum Resistant Public Key Exchange: The Supersingular Isogenous Diffie-Hellman Protocol – CoinFabrik Blog"
.
blog.coinfabrik.com
. 13 October 2016.
Archived
from the original on 2 February 2017
. Retrieved
24 January
2017
.
- ↑Thapliyal, K.; Pathak, A. (2018). "Kak's three-stage protocol of secure quantum communication revisited".Quantum Information Processing.17(9): 229.arXiv:1803.02157.Bibcode:2018QuIP...17..229T.doi:10.1007/s11128-018-2001-z.S2CID52009384.
↑
Thapliyal, K.; Pathak, A. (2018). "Kak's three-stage protocol of secure quantum communication revisited".
Quantum Information Processing
.
17
(9): 229.
arXiv
:
1803.02157
.
Bibcode
:
2018QuIP...17..229T
.
doi
:
10.1007/s11128-018-2001-z
.
S2CID
52009384
.
- ↑Nikolopoulos, Georgios M.; Fischlin, Marc (2020)."Information-Theoretically Secure Data Origin Authentication with Quantum and Classical Resources".Cryptography.4(4): 31.arXiv:2011.06849.doi:10.3390/cryptography4040031.S2CID226956062.
↑
Nikolopoulos, Georgios M.; Fischlin, Marc (2020).
"Information-Theoretically Secure Data Origin Authentication with Quantum and Classical Resources"
.
Cryptography
.
4
(4): 31.
arXiv
:
2011.06849
.
doi
:
10.3390/cryptography4040031
.
S2CID
226956062
.
- ↑Doescher, C.; Keyl, M. (2001). "Quantum Digital Signatures".arXiv:quant-ph/0105032.
↑
Doescher, C.; Keyl, M. (2001). "Quantum Digital Signatures".
arXiv
:
quant-ph/0105032
.
- ↑Collins, Robert J.; Donaldson, Ross J.; Dunjko, Vedran; Wallden, Petros; Clarke, Patrick J.; Andersson, Erika; Jeffers, John; Buller, Gerald S. (2014). "Realization of Quantum Digital Signatures without the Requirement of Quantum Memory".Physical Review Letters.113(4) 040502.arXiv:1311.5760.Bibcode:2014PhRvL.113d0502C.doi:10.1103/PhysRevLett.113.040502.PMID25105603.S2CID23925266.
↑
Collins, Robert J.; Donaldson, Ross J.; Dunjko, Vedran; Wallden, Petros; Clarke, Patrick J.; Andersson, Erika; Jeffers, John; Buller, Gerald S. (2014). "Realization of Quantum Digital Signatures without the Requirement of Quantum Memory".
Physical Review Letters
.
113
(4) 040502.
arXiv
:
1311.5760
.
Bibcode
:
2014PhRvL.113d0502C
.
doi
:
10.1103/PhysRevLett.113.040502
.
PMID
25105603
.
S2CID
23925266
.
- ↑Kawachi, Akinori; Koshiba, Takeshi; Nishimura, Harumichi; Yamakami, Tomoyuki (2011). "Computational Indistinguishability Between Quantum States and its Cryptographic Application".Journal of Cryptology.25(3):528–555.arXiv:quant-ph/0403069.CiteSeerX10.1.1.251.6055.doi:10.1007/s00145-011-9103-4.S2CID6340239.
↑
Kawachi, Akinori; Koshiba, Takeshi; Nishimura, Harumichi; Yamakami, Tomoyuki (2011). "Computational Indistinguishability Between Quantum States and its Cryptographic Application".
Journal of Cryptology
.
25
(3):
528–
555.
arXiv
:
quant-ph/0403069
.
CiteSeerX
10.1.1.251.6055
.
doi
:
10.1007/s00145-011-9103-4
.
S2CID
6340239
.
- ↑Kabashima, Yoshiyuki; Murayama, Tatsuto; Saad, David (2000). "Cryptographical Properties of Ising Spin Systems".Physical Review Letters.84(9):2030–2033.arXiv:cond-mat/0002129.Bibcode:2000PhRvL..84.2030K.doi:10.1103/PhysRevLett.84.2030.PMID11017688.S2CID12883829.
↑
Kabashima, Yoshiyuki; Murayama, Tatsuto; Saad, David (2000). "Cryptographical Properties of Ising Spin Systems".
Physical Review Letters
.
84
(9):
2030–
2033.
arXiv
:
cond-mat/0002129
.
Bibcode
:
2000PhRvL..84.2030K
.
doi
:
10.1103/PhysRevLett.84.2030
.
PMID
11017688
.
S2CID
12883829
.
- ↑Nikolopoulos, Georgios M. (2008). "Applications of single-qubit rotations in quantum public-key cryptography".Physical Review A.77(3) 032348.arXiv:0801.2840.Bibcode:2008PhRvA..77c2348N.doi:10.1103/PhysRevA.77.032348.S2CID119097757.
↑
Nikolopoulos, Georgios M. (2008). "Applications of single-qubit rotations in quantum public-key cryptography".
Physical Review A
.
77
(3) 032348.
arXiv
:
0801.2840
.
Bibcode
:
2008PhRvA..77c2348N
.
doi
:
10.1103/PhysRevA.77.032348
.
S2CID
119097757
.
- ↑Nikolopoulos, Georgios M.; Ioannou, Lawrence M. (2009). "Deterministic quantum-public-key encryption: Forward search attack and randomization".Physical Review A.79(4) 042327.arXiv:0903.4744.Bibcode:2009PhRvA..79d2327N.doi:10.1103/PhysRevA.79.042327.S2CID118425296.
↑
Nikolopoulos, Georgios M.; Ioannou, Lawrence M. (2009). "Deterministic quantum-public-key encryption: Forward search attack and randomization".
Physical Review A
.
79
(4) 042327.
arXiv
:
0903.4744
.
Bibcode
:
2009PhRvA..79d2327N
.
doi
:
10.1103/PhysRevA.79.042327
.
S2CID
118425296
.
- ↑Seyfarth, U.; Nikolopoulos, G. M.; Alber, G. (2012). "Symmetries and security of a quantum-public-key encryption based on single-qubit rotations".Physical Review A.85(2) 022342.arXiv:1202.3921.Bibcode:2012PhRvA..85b2342S.doi:10.1103/PhysRevA.85.022342.S2CID59467718.
↑
Seyfarth, U.; Nikolopoulos, G. M.; Alber, G. (2012). "Symmetries and security of a quantum-public-key encryption based on single-qubit rotations".
Physical Review A
.
85
(2) 022342.
arXiv
:
1202.3921
.
Bibcode
:
2012PhRvA..85b2342S
.
doi
:
10.1103/PhysRevA.85.022342
.
S2CID
59467718
.
- ↑Nikolopoulos, Georgios M.; Brougham, Thomas (11 July 2016)."Decision and function problems based on boson sampling".Physical Review A.94(1) 012315.arXiv:1607.02987.Bibcode:2016PhRvA..94a2315N.doi:10.1103/PhysRevA.94.012315.S2CID5311008.
↑
Nikolopoulos, Georgios M.; Brougham, Thomas (11 July 2016).
"Decision and function problems based on boson sampling"
.
Physical Review A
.
94
(1) 012315.
arXiv
:
1607.02987
.
Bibcode
:
2016PhRvA..94a2315N
.
doi
:
10.1103/PhysRevA.94.012315
.
S2CID
5311008
.
- ↑Nikolopoulos, Georgios M. (13 July 2019). "Cryptographic one-way function based on boson sampling".Quantum Information Processing.18(8) 259.arXiv:1907.01788.Bibcode:2019QuIP...18..259N.doi:10.1007/s11128-019-2372-9.ISSN1573-1332.S2CID195791867.
↑
Nikolopoulos, Georgios M. (13 July 2019). "Cryptographic one-way function based on boson sampling".
Quantum Information Processing
.
18
(8) 259.
arXiv
:
1907.01788
.
Bibcode
:
2019QuIP...18..259N
.
doi
:
10.1007/s11128-019-2372-9
.
ISSN
1573-1332
.
S2CID
195791867
.
- ↑Nikolopoulos, Georgios M. (16 January 2025)."Quantum Diffie–Hellman key exchange".APL Quantum.2(1) 016107.arXiv:2501.09568.doi:10.1063/5.0242473.ISSN2835-0103.
↑
Nikolopoulos, Georgios M. (16 January 2025).
"Quantum Diffie–Hellman key exchange"
.
APL Quantum
.
2
(1) 016107.
arXiv
:
2501.09568
.
doi
:
10.1063/5.0242473
.
ISSN
2835-0103
.
- ↑Buhrman, Harry; Cleve, Richard; Watrous, John; De Wolf, Ronald (2001). "Quantum Fingerprinting".Physical Review Letters.87(16) 167902.arXiv:quant-ph/0102001.Bibcode:2001PhRvL..87p7902B.doi:10.1103/PhysRevLett.87.167902.PMID11690244.S2CID1096490.
↑
Buhrman, Harry; Cleve, Richard; Watrous, John; De Wolf, Ronald (2001). "Quantum Fingerprinting".
Physical Review Letters
.
87
(16) 167902.
arXiv
:
quant-ph/0102001
.
Bibcode
:
2001PhRvL..87p7902B
.
doi
:
10.1103/PhysRevLett.87.167902
.
PMID
11690244
.
S2CID
1096490
.
- ↑Nikolopoulos, Georgios M.; Diamanti, Eleni (10 April 2017)."Continuous-variable quantum authentication of physical unclonable keys".Scientific Reports.7(1) 46047.arXiv:1704.06146.Bibcode:2017NatSR...746047N.doi:10.1038/srep46047.ISSN2045-2322.PMC5385567.PMID28393853.
↑
Nikolopoulos, Georgios M.; Diamanti, Eleni (10 April 2017).
"Continuous-variable quantum authentication of physical unclonable keys"
.
Scientific Reports
.
7
(1) 46047.
arXiv
:
1704.06146
.
Bibcode
:
2017NatSR...746047N
.
doi
:
10.1038/srep46047
.
ISSN
2045-2322
.
PMC
5385567
.
PMID
28393853
.
- ↑Nikolopoulos, Georgios M. (22 January 2018)."Continuous-variable quantum authentication of physical unclonable keys: Security against an emulation attack".Physical Review A.97(1) 012324.arXiv:1801.07434.Bibcode:2018PhRvA..97a2324N.doi:10.1103/PhysRevA.97.012324.S2CID119486945.
↑
Nikolopoulos, Georgios M. (22 January 2018).
"Continuous-variable quantum authentication of physical unclonable keys: Security against an emulation attack"
.
Physical Review A
.
97
(1) 012324.
arXiv
:
1801.07434
.
Bibcode
:
2018PhRvA..97a2324N
.
doi
:
10.1103/PhysRevA.97.012324
.
S2CID
119486945
.
- ↑Fladung, Lukas; Nikolopoulos, Georgios M.; Alber, Gernot; Fischlin, Marc (2019)."Intercept-Resend Emulation Attacks against a Continuous-Variable Quantum Authentication Protocol with Physical Unclonable Keys".Cryptography.3(4): 25.arXiv:1910.11579.doi:10.3390/cryptography3040025.S2CID204901444.
↑
Fladung, Lukas; Nikolopoulos, Georgios M.; Alber, Gernot; Fischlin, Marc (2019).
"Intercept-Resend Emulation Attacks against a Continuous-Variable Quantum Authentication Protocol with Physical Unclonable Keys"
.
Cryptography
.
3
(4): 25.
arXiv
:
1910.11579
.
doi
:
10.3390/cryptography3040025
.
S2CID
204901444
.
- ↑Barbosa, Geraldo A.; Corndorf, Eric; Kumar, Prem; Yuen, Horace P. (2 June 2003). "Secure Communication Using Mesoscopic Coherent States".Physical Review Letters.90(22) 227901.arXiv:quant-ph/0212018.Bibcode:2003PhRvL..90v7901B.doi:10.1103/PhysRevLett.90.227901.PMID12857341.S2CID12720233.
↑
Barbosa, Geraldo A.; Corndorf, Eric; Kumar, Prem; Yuen, Horace P. (2 June 2003). "Secure Communication Using Mesoscopic Coherent States".
Physical Review Letters
.
90
(22) 227901.
arXiv
:
quant-ph/0212018
.
Bibcode
:
2003PhRvL..90v7901B
.
doi
:
10.1103/PhysRevLett.90.227901
.
PMID
12857341
.
S2CID
12720233
.
- ↑Yuen, H. P. (31 July 2009).Physical Cryptography: A New Approach to Key Generation and Direct Encryption(PDF)(PhD thesis).
↑
Yuen, H. P. (31 July 2009).
Physical Cryptography: A New Approach to Key Generation and Direct Encryption
(PDF)
(PhD thesis).
- 12Verma, Pramode K.; El Rifai, Mayssaa; Chan, K. W. Clifford (19 August 2018)."Secure Communication Based on Quantum Noise".Multi-photon Quantum Secure Communication. Signals and Communication Technology. pp.85–95.doi:10.1007/978-981-10-8618-2_4.ISBN978-981-10-8617-5.S2CID56788374.
1
2
Verma, Pramode K.; El Rifai, Mayssaa; Chan, K. W. Clifford (19 August 2018).
"Secure Communication Based on Quantum Noise"
.
Multi-photon Quantum Secure Communication
. Signals and Communication Technology. pp.
85–
95.
doi
:
10.1007/978-981-10-8618-2_4
.
ISBN
978-981-10-8617-5
.
S2CID
56788374
.
- 12Takehisa, Iwakoshi (27 January 2020)."Analysis of Y00 Protocol Under Quantum Generalization of a Fast Correlation Attack: Toward Information-Theoretic Security".IEEE Access.8:23417–23426.arXiv:2001.11150.Bibcode:2020IEEEA...823417I.doi:10.1109/ACCESS.2020.2969455.S2CID210966407.
1
2
Takehisa, Iwakoshi (27 January 2020).
"Analysis of Y00 Protocol Under Quantum Generalization of a Fast Correlation Attack: Toward Information-Theoretic Security"
.
IEEE Access
.
8
:
23417–
23426.
arXiv
:
2001.11150
.
Bibcode
:
2020IEEEA...823417I
.
doi
:
10.1109/ACCESS.2020.2969455
.
S2CID
210966407
.
- ↑Hirota, Osamu; etal. (1 September 2010). "Getting around the Shannon limit of cryptography".SPIE Newsroom.doi:10.1117/2.1201008.003069.
↑
Hirota, Osamu; et
al. (1 September 2010). "Getting around the Shannon limit of cryptography".
SPIE Newsroom
.
doi
:
10.1117/2.1201008.003069
.
- ↑Quan, Yu; etal. (30 March 2020)."Secure 100Gb/s IMDD transmission over 100 km SSMF enabled by quantum noise stream cipher and sparse RLS-Volterra equalizer".IEEE Access.8:63585–63594.Bibcode:2020IEEEA...863585Y.doi:10.1109/ACCESS.2020.2984330.S2CID215816092.
↑
Quan, Yu; et
al. (30 March 2020).
"Secure 100Gb/s IMDD transmission over 100 km SSMF enabled by quantum noise stream cipher and sparse RLS-Volterra equalizer"
.
IEEE Access
.
8
:
63585–
63594.
Bibcode
:
2020IEEEA...863585Y
.
doi
:
10.1109/ACCESS.2020.2984330
.
S2CID
215816092
.
- ↑Wyner, A. D. (October 1975). "The Wire-Tap Channel".Bell System Technical Journal.54(8):1355–1387.Bibcode:1975BSTJ...54.1355W.doi:10.1002/j.1538-7305.1975.tb02040.x.S2CID21512925.
↑
Wyner, A. D. (October 1975). "The Wire-Tap Channel".
Bell System Technical Journal
.
54
(8):
1355–
1387.
Bibcode
:
1975BSTJ...54.1355W
.
doi
:
10.1002/j.1538-7305.1975.tb02040.x
.
S2CID
21512925
.
- ↑Roy J., Glauber (15 June 1963)."The Quantum Theory of Optical Coherence".Physical Review.130(6):2529–2539.Bibcode:1963PhRv..130.2529G.doi:10.1103/PhysRev.130.2529.
↑
Roy J., Glauber (15 June 1963).
"The Quantum Theory of Optical Coherence"
.
Physical Review
.
130
(6):
2529–
2539.
Bibcode
:
1963PhRv..130.2529G
.
doi
:
10.1103/PhysRev.130.2529
.
- ↑E. C. G., Sudarshan (1 April 1963). "Equivalence of Semiclassical and Quantum Mechanical Descriptions of Statistical Light Beams".Physical Review Letters.10(7):277–279.Bibcode:1963PhRvL..10..277S.doi:10.1103/PhysRevLett.10.277.
↑
E. C. G., Sudarshan (1 April 1963). "Equivalence of Semiclassical and Quantum Mechanical Descriptions of Statistical Light Beams".
Physical Review Letters
.
10
(7):
277–
279.
Bibcode
:
1963PhRvL..10..277S
.
doi
:
10.1103/PhysRevLett.10.277
.
- ↑Walls, D. F.; Milburn, G. J. (January 2008).Quantum optics. Springer.ISBN978-3-540-28573-1.
↑
Walls, D. F.; Milburn, G. J. (January 2008).
Quantum optics
. Springer.
ISBN
978-3-540-28573-1
.
- ↑Hirota, Osamu; etal. (26 August 2005). "Quantum stream cipher by the Yuen 2000 protocol: Design and experiment by an intensity-modulation scheme".Physical Review A.72(2) 022335.arXiv:quant-ph/0507043.Bibcode:2005PhRvA..72b2335H.doi:10.1103/PhysRevA.72.022335.S2CID118937168.
↑
Hirota, Osamu; et
al. (26 August 2005). "Quantum stream cipher by the Yuen 2000 protocol: Design and experiment by an intensity-modulation scheme".
Physical Review A
.
72
(2) 022335.
arXiv
:
quant-ph/0507043
.
Bibcode
:
2005PhRvA..72b2335H
.
doi
:
10.1103/PhysRevA.72.022335
.
S2CID
118937168
.
- ↑Yoshida, Masato; etal. (15 February 2021). "10 Tbit/s QAM Quantum Noise Stream Cipher Coherent Transmission Over 160 Km".Journal of Lightwave Technology.39(4):1056–1063.Bibcode:2021JLwT...39.1056Y.doi:10.1109/JLT.2020.3016693.S2CID225383926.
↑
Yoshida, Masato; et
al. (15 February 2021). "10 Tbit/s QAM Quantum Noise Stream Cipher Coherent Transmission Over 160 Km".
Journal of Lightwave Technology
.
39
(4):
1056–
1063.
Bibcode
:
2021JLwT...39.1056Y
.
doi
:
10.1109/JLT.2020.3016693
.
S2CID
225383926
.
- ↑Futami, Fumio; etal. (March 2018)."Dynamic Routing of Y-00 Quantum Stream Cipher in Field-Deployed Dynamic Optical Path Network".Optical Fiber Communication Conference.doi:10.1364/OFC.2018.Tu2G.5.ISBN978-1-943580-38-5.S2CID49185664.
↑
Futami, Fumio; et
al. (March 2018).
"Dynamic Routing of Y-00 Quantum Stream Cipher in Field-Deployed Dynamic Optical Path Network"
.
Optical Fiber Communication Conference
.
doi
:
10.1364/OFC.2018.Tu2G.5
.
ISBN
978-1-943580-38-5
.
S2CID
49185664
.
- ↑Tanizawa, Ken; Futami, Fumio (2020)."Security-Enhanced 10, 118-km Single-Channel 40-Gbit/s Transmission Using PSK Y-00 Quantum Stream Cipher".2020 European Conference on Optical Communications (ECOC). pp.1–4.doi:10.1109/ECOC48923.2020.9333304.ISBN978-1-7281-7361-0.S2CID231852229.
↑
Tanizawa, Ken; Futami, Fumio (2020).
"Security-Enhanced 10, 118-km Single-Channel 40-Gbit/s Transmission Using PSK Y-00 Quantum Stream Cipher"
.
2020 European Conference on Optical Communications (ECOC)
. pp.
1–
4.
doi
:
10.1109/ECOC48923.2020.9333304
.
ISBN
978-1-7281-7361-0
.
S2CID
231852229
.
- ↑Tanizawa, Ken; Futami, Fumio (April 2020)."Quantum Noise-Assisted Coherent Radio-over-Fiber Cipher System for Secure Optical Fronthaul and Microwave Wireless Links".Journal of Lightwave Technology.38(16):4244–4249.Bibcode:2020JLwT...38.4244T.doi:10.1109/JLT.2020.2987213.S2CID219095947.
↑
Tanizawa, Ken; Futami, Fumio (April 2020).
"Quantum Noise-Assisted Coherent Radio-over-Fiber Cipher System for Secure Optical Fronthaul and Microwave Wireless Links"
.
Journal of Lightwave Technology
.
38
(16):
4244–
4249.
Bibcode
:
2020JLwT...38.4244T
.
doi
:
10.1109/JLT.2020.2987213
.
S2CID
219095947
.
- ↑Yuen, Horace P. (November 2009). "Key Generation: Foundations and a New Quantum Approach".IEEE Journal of Selected Topics in Quantum Electronics.15(6):1630–1645.arXiv:0906.5241.Bibcode:2009IJSTQ..15.1630Y.doi:10.1109/JSTQE.2009.2025698.S2CID867791.
↑
Yuen, Horace P. (November 2009). "Key Generation: Foundations and a New Quantum Approach".
IEEE Journal of Selected Topics in Quantum Electronics
.
15
(6):
1630–
1645.
arXiv
:
0906.5241
.
Bibcode
:
2009IJSTQ..15.1630Y
.
doi
:
10.1109/JSTQE.2009.2025698
.
S2CID
867791
.
- ↑Iwakoshi, Takehisa (5 June 2019)."Message-Falsification Prevention With Small Quantum Mask in Quaternary Y00 Protocol".IEEE Access.7:74482–74489.Bibcode:2019IEEEA...774482I.doi:10.1109/ACCESS.2019.2921023.S2CID195225370.
↑
Iwakoshi, Takehisa (5 June 2019).
"Message-Falsification Prevention With Small Quantum Mask in Quaternary Y00 Protocol"
.
IEEE Access
.
7
:
74482–
74489.
Bibcode
:
2019IEEEA...774482I
.
doi
:
10.1109/ACCESS.2019.2921023
.
S2CID
195225370
.
- ↑Nishioka, Tsuyoshi; etal. (21 June 2004). "How much security does Y-00 protocol provide us?".Physics Letters A.327(1):28–32.arXiv:quant-ph/0310168.Bibcode:2004PhLA..327...28N.doi:10.1016/j.physleta.2004.04.083.S2CID119069709.
↑
Nishioka, Tsuyoshi; et
al. (21 June 2004). "How much security does Y-00 protocol provide us?".
Physics Letters A
.
327
(1):
28–
32.
arXiv
:
quant-ph/0310168
.
Bibcode
:
2004PhLA..327...28N
.
doi
:
10.1016/j.physleta.2004.04.083
.
S2CID
119069709
.
- ↑Yuen, Horace P.; etal. (10 October 2005). "Comment on:'How much security does Y-00 protocol provide us?'[Phys. Lett. A 327 (2004) 28]".Physics Letters A.346(1–3):1–6.Bibcode:2005PhLA..346....1Y.doi:10.1016/j.physleta.2005.08.022.
↑
Yuen, Horace P.; et
al. (10 October 2005). "Comment on:'How much security does Y-00 protocol provide us?'[Phys. Lett. A 327 (2004) 28]".
Physics Letters A
.
346
(
1–
3):
1–
6.
Bibcode
:
2005PhLA..346....1Y
.
doi
:
10.1016/j.physleta.2005.08.022
.
- ↑Nishioka, Tsuyoshi; etal. (10 October 2005). "Reply to:"Comment on:'How much security does Y-00 protocol provide us?'" [Phys. Lett. A 346 (2005) 1]".Physics Letters A.346(1–3).Bibcode:2005PhLA..346....1Y.doi:10.1016/j.physleta.2005.08.022.
↑
Nishioka, Tsuyoshi; et
al. (10 October 2005). "Reply to:"Comment on:'How much security does Y-00 protocol provide us?'" [Phys. Lett. A 346 (2005) 1]".
Physics Letters A
.
346
(
1–
3).
Bibcode
:
2005PhLA..346....1Y
.
doi
:
10.1016/j.physleta.2005.08.022
.
- ↑Nair, Ranjith; etal. (13 September 2005). "Reply to:'Reply to:"Comment on:'How much security does Y-00 protocol provide us?'"'".arXiv:quant-ph/0509092.
↑
Nair, Ranjith; et
al. (13 September 2005). "Reply to:'Reply to:"Comment on:'How much security does Y-00 protocol provide us?'"'
".
arXiv
:
quant-ph/0509092
.
- ↑Donnet, Stéphane; etal. (21 August 2006). "Security of Y-00 under heterodyne measurement and fast correlation attack".Physics Letters A.356(6):406–410.Bibcode:2006PhLA..356..406D.doi:10.1016/j.physleta.2006.04.002.
↑
Donnet, Stéphane; et
al. (21 August 2006). "Security of Y-00 under heterodyne measurement and fast correlation attack".
Physics Letters A
.
356
(6):
406–
410.
Bibcode
:
2006PhLA..356..406D
.
doi
:
10.1016/j.physleta.2006.04.002
.
- ↑Yuen, Horace P.; etal. (23 April 2007). "On the security of Y-00 under fast correlation and other attacks on the key".Physics Letters A.364(2):112–116.arXiv:quant-ph/0608028.Bibcode:2007PhLA..364..112Y.doi:10.1016/j.physleta.2006.12.033.S2CID7824483.
↑
Yuen, Horace P.; et
al. (23 April 2007). "On the security of Y-00 under fast correlation and other attacks on the key".
Physics Letters A
.
364
(2):
112–
116.
arXiv
:
quant-ph/0608028
.
Bibcode
:
2007PhLA..364..112Y
.
doi
:
10.1016/j.physleta.2006.12.033
.
S2CID
7824483
.
- ↑Mihaljević, Miodrag J. (24 May 2007). "Generic framework for the secure Yuen 2000 quantum-encryption protocol employing the wire-tap channel approach".Physical Review A.75(5) 052334.Bibcode:2007PhRvA..75e2334M.doi:10.1103/PhysRevA.75.052334.
↑
Mihaljević, Miodrag J. (24 May 2007). "Generic framework for the secure Yuen 2000 quantum-encryption protocol employing the wire-tap channel approach".
Physical Review A
.
75
(5) 052334.
Bibcode
:
2007PhRvA..75e2334M
.
doi
:
10.1103/PhysRevA.75.052334
.
- ↑Shimizu, Tetsuya; etal. (27 March 2008). "Running key mapping in a quantum stream cipher by the Yuen 2000 protocol".Physical Review A.77(3) 034305.Bibcode:2008PhRvA..77c4305S.doi:10.1103/PhysRevA.77.034305.
↑
Shimizu, Tetsuya; et
al. (27 March 2008). "Running key mapping in a quantum stream cipher by the Yuen 2000 protocol".
Physical Review A
.
77
(3) 034305.
Bibcode
:
2008PhRvA..77c4305S
.
doi
:
10.1103/PhysRevA.77.034305
.
- ↑Tregubov, P. A.; Trushechkin, A. S. (21 November 2020). "Quantum Stream Ciphers: Impossibility of Unconditionally Strong Algorithms".Journal of Mathematical Sciences.252:90–103.doi:10.1007/s10958-020-05144-x.S2CID254745640.
↑
Tregubov, P. A.; Trushechkin, A. S. (21 November 2020). "Quantum Stream Ciphers: Impossibility of Unconditionally Strong Algorithms".
Journal of Mathematical Sciences
.
252
:
90–
103.
doi
:
10.1007/s10958-020-05144-x
.
S2CID
254745640
.
- ↑Iwakoshi, Takehisa (February 2021)."Security Evaluation of Y00 Protocol Based on Time-Translational Symmetry Under Quantum Collective Known-Plaintext Attacks".IEEE Access.9:31608–31617.Bibcode:2021IEEEA...931608I.doi:10.1109/ACCESS.2021.3056494.S2CID232072394.
↑
Iwakoshi, Takehisa (February 2021).
"Security Evaluation of Y00 Protocol Based on Time-Translational Symmetry Under Quantum Collective Known-Plaintext Attacks"
.
IEEE Access
.
9
:
31608–
31617.
Bibcode
:
2021IEEEA...931608I
.
doi
:
10.1109/ACCESS.2021.3056494
.
S2CID
232072394
.
- ↑Scarani, Valerio; Bechmann-Pasquinucci, Helle; Cerf, Nicolas J.; Dušek, Miloslav; Lütkenhaus, Norbert; Peev, Momtchil (29 September 2009). "The security of practical quantum key distribution".Reviews of Modern Physics.81(3):1301–1350.arXiv:0802.4155.Bibcode:2009RvMP...81.1301S.doi:10.1103/revmodphys.81.1301.ISSN0034-6861.S2CID15873250.
↑
Scarani, Valerio; Bechmann-Pasquinucci, Helle; Cerf, Nicolas J.; Dušek, Miloslav; Lütkenhaus, Norbert; Peev, Momtchil (29 September 2009). "The security of practical quantum key distribution".
Reviews of Modern Physics
.
81
(3):
1301–
1350.
arXiv
:
0802.4155
.
Bibcode
:
2009RvMP...81.1301S
.
doi
:
10.1103/revmodphys.81.1301
.
ISSN
0034-6861
.
S2CID
15873250
.
- 123Zhao, Yi (2009).Quantum cryptography in real-life applications: assumptions and security(PDF)(Thesis).Bibcode:2009PhDT........94Z.S2CID118227839. Archived fromthe original(PDF)on 28 February 2020.
1
2
3
Zhao, Yi (2009).
Quantum cryptography in real-life applications: assumptions and security
(PDF)
(Thesis).
Bibcode
:
2009PhDT........94Z
.
S2CID
118227839
. Archived from
the original
(PDF)
on 28 February 2020.
- 1234Lo, Hoi-Kwong (22 October 2005). "Decoy State Quantum Key Distribution".Quantum Information Science.94(23). WORLD SCIENTIFIC: 143.arXiv:quant-ph/0411004.Bibcode:2005qis..conf..143L.doi:10.1142/9789812701633_0013.ISBN978-981-256-460-3.PMID16090452.
1
2
3
4
Lo, Hoi-Kwong (22 October 2005). "Decoy State Quantum Key Distribution".
Quantum Information Science
.
94
(23). WORLD SCIENTIFIC: 143.
arXiv
:
quant-ph/0411004
.
Bibcode
:
2005qis..conf..143L
.
doi
:
10.1142/9789812701633_0013
.
ISBN
978-981-256-460-3
.
PMID
16090452
.
- ↑Reimer, Michael E.; Cher, Catherine (November 2019)."The quest for a perfect single-photon source".Nature Photonics.13(11):734–736.Bibcode:2019NaPho..13..734R.doi:10.1038/s41566-019-0544-x.ISSN1749-4893.S2CID209939102.
↑
Reimer, Michael E.; Cher, Catherine (November 2019).
"The quest for a perfect single-photon source"
.
Nature Photonics
.
13
(11):
734–
736.
Bibcode
:
2019NaPho..13..734R
.
doi
:
10.1038/s41566-019-0544-x
.
ISSN
1749-4893
.
S2CID
209939102
.
- 123456Makarov, Vadim; Anisimov, Andrey; Skaar, Johannes (31 July 2008)."Erratum: Effects of detector efficiency mismatch on security of quantum cryptosystems[Phys. Rev. A74, 022313 (2006)]".Physical Review A.78(1) 019905.Bibcode:2008PhRvA..78a9905M.doi:10.1103/physreva.78.019905.ISSN1050-2947.
1
2
3
4
5
6
Makarov, Vadim; Anisimov, Andrey; Skaar, Johannes (31 July 2008).
"Erratum: Effects of detector efficiency mismatch on security of quantum cryptosystems
[
Phys. Rev. A74, 022313 (2006)
]
"
.
Physical Review A
.
78
(1) 019905.
Bibcode
:
2008PhRvA..78a9905M
.
doi
:
10.1103/physreva.78.019905
.
ISSN
1050-2947
.
- 12"Quantum Key Distribution (QKD) and Quantum Cryptography (QC)".National Security Agency. Retrieved16 July2022.This article incorporates text from this source, which is in thepublic domain.
1
2
"Quantum Key Distribution (QKD) and Quantum Cryptography (QC)"
.
National Security Agency
. Retrieved
16 July
2022
.
This article incorporates text from this source, which is in the
public domain
.
- ↑Post-Quantum Cryptography: Current state and quantum mitigation, Section 6 "Conclusion"
↑
Post-Quantum Cryptography: Current state and quantum mitigation, Section 6 "Conclusion"
- ↑Quantum security technologies
↑
Quantum security technologies
- ↑Should Quantum Key Distribution be Used for Secure Communications?
↑
Should Quantum Key Distribution be Used for Secure Communications?
- ↑"Quantum Cryptography".
↑
"Quantum Cryptography"
.
- ↑"Planning for post-quantum cryptography". Archived fromthe originalon 14 September 2025. Retrieved12 September2025.
↑
"Planning for post-quantum cryptography"
. Archived from
the original
on 14 September 2025
. Retrieved
12 September
2025
.
- ↑"Position Paper on Quantum Key Distribution"(PDF).
↑
"Position Paper on Quantum Key Distribution"
(PDF)
.
- ↑Scarani, Valerio; Kurtsiefer, Christian (4 December 2014). "The black paper of quantum cryptography: Real implementation problems".Theoretical Computer Science.560:27–32.arXiv:0906.4547.doi:10.1016/j.tcs.2014.09.015.S2CID44504715.
↑
Scarani, Valerio; Kurtsiefer, Christian (4 December 2014). "The black paper of quantum cryptography: Real implementation problems".
Theoretical Computer Science
.
560
:
27–
32.
arXiv
:
0906.4547
.
doi
:
10.1016/j.tcs.2014.09.015
.
S2CID
44504715
.
- ↑Pacher, Christoph; et, al. (January 2016). "Attacks on quantum key distribution protocols that employ non-ITS authentication".Quantum Information Processing.15(1):327–362.arXiv:1209.0365.Bibcode:2016QuIP...15..327P.doi:10.1007/s11128-015-1160-4.S2CID254986932.
↑
Pacher, Christoph; et, al. (January 2016). "Attacks on quantum key distribution protocols that employ non-ITS authentication".
Quantum Information Processing
.
15
(1):
327–
362.
arXiv
:
1209.0365
.
Bibcode
:
2016QuIP...15..327P
.
doi
:
10.1007/s11128-015-1160-4
.
S2CID
254986932
.
- ↑Mattsson, J. P.; etal. (December 2021). "Quantum-Resistant Cryptography".arXiv:2112.00399[cs.CR].
↑
Mattsson, J. P.; et
al. (December 2021). "Quantum-Resistant Cryptography".
arXiv
:
2112.00399
[
cs.CR
].
- ↑Bloom, Yuval; Fields, Ilai; Maslennikov, Alona; Rozenman, Georgi Gary (2022)."Quantum Cryptography—A Simplified Undergraduate Experiment and Simulation".Physics.4(1):104–123.Bibcode:2022Physi...4..104B.doi:10.3390/physics4010009.
↑
Bloom, Yuval; Fields, Ilai; Maslennikov, Alona; Rozenman, Georgi Gary (2022).
"Quantum Cryptography—A Simplified Undergraduate Experiment and Simulation"
.
Physics
.
4
(1):
104–
123.
Bibcode
:
2022Physi...4..104B
.
doi
:
10.3390/physics4010009
.

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

<!-- table omitted -->

- v
v
- t
t
- e
e
Emerging technologies
Fields

<!-- table omitted -->

Quantum
- algorithms
algorithms
- amplifier
amplifier
- bus
bus
- cellular automata
cellular automata
- channel
channel
- circuit
circuit
- complexity theory
complexity theory
- computing
computing
- cryptographypost-quantum
cryptography
- post-quantum
post-quantum
- dynamics
dynamics
- electronics
electronics
- error correction
error correction
- finite automata
finite automata
- image processing
image processing
- imaging
imaging
- information
information
- key distribution
key distribution
- logic
logic
- logic clock
logic clock
- logic gate
logic gate
- machine
machine
- machine learning
machine learning
- metamaterial
metamaterial
- network
network
- neural network
neural network
- optics
optics
- programming
programming
- sensing
sensing
- simulator
simulator
- teleportation
teleportation
Other
- Acoustic levitation
Acoustic levitation
- Anti-gravity
Anti-gravity
- Cloak of invisibility
Cloak of invisibility
- Digital scent technology
Digital scent technology
- Force fieldPlasma window
Force field
- Plasma window
Plasma window
- Immersive virtual reality
Immersive virtual reality
- Magnetic refrigeration
Magnetic refrigeration
- Phased-array optics
Phased-array optics
- Thermoacoustic heat engine
Thermoacoustic heat engine
- List
List

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

Authority control databases
: National
- Japan
Japan
NewPP limit report
Parsed by mw‐api‐int.eqiad.main‐54bb4c5f8b‐slwnq
Cached time: 20260629235114
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, show‐toc, prevent‐selective‐update, use‐parsoid]
CPU time usage: 3.125 seconds
Real time usage: 3.482 seconds
Preprocessor visited node count: 7087/1000000
Revision size: 86546/2097152 bytes
Post‐expand include size: 419649/2097152 bytes
Template argument size: 3567/2097152 bytes
Highest expansion depth: 17/100
Expensive parser function count: 8/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 343107/5000000 bytes
Lua time usage: 0.769/10.000 seconds
Lua memory usage: 6560477/52428800 bytes
Number of Wikibase entities loaded: 1/500
Transclusion expansion time report (%,ms,calls,template)
100.00% 2596.588      1 -total
 21.00%  545.340     88 Template:Cite_journal
  2.77%   71.957      8 Template:Navbox
  2.53%   65.567      1 Template:Short_description
  1.91%   49.712     10 Template:Cite_book
  1.84%   47.725     12 Template:Cite_web
  1.77%   45.895      8 Template:Cite_conference
  1.52%   39.590      2 Template:Pagetype
  1.32%   34.174      1 Template:Page_needed
  1.18%   30.657      1 Template:Fix
Render ID 699995c2-7415-11f1-968e-a1a715267053
Saved in parser cache with key enwiki:parsoid-pcache:28676005:|#|:idhash:useParsoid=1 and timestamp 20260629235114 and revision id 1360673943. Rendering was triggered because: MediaWiki\Rest\Handler\Helper\HtmlOutputRendererHelper::getParserOutput
Parsoid 0.24.0.0-alpha12
Post‐processing cache key enwiki:postproc‐parsoid‐pcache:28676005:|#|:idhash:injectTOC=0!postproc=1!skin=vector‐2022!useParsoid=1!visibleLinks=wtsingle, generated at 20260630001101
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Quantum_cryptography&oldid=1360673943
"
Category
:
- Quantum cryptography
Quantum cryptography
Hidden categories:
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Use dmy dates from December 2025
Use dmy dates from December 2025
- Wikipedia articles needing page number citations from December 2025
Wikipedia articles needing page number citations from December 2025
- Source attribution
Source attribution