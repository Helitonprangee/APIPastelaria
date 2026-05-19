from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

# 🔥 COLOCA SEU NOME COMPLETO AQUI
nome_completo = "Heliton marcondes prange"

# cria chave privada
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# dados do certificado
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SC"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, "Otacilio Costa"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, nome_completo),
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

cert = x509.CertificateBuilder()\
    .subject_name(subject)\
    .issuer_name(issuer)\
    .public_key(key.public_key())\
    .serial_number(x509.random_serial_number())\
    .not_valid_before(datetime.datetime.utcnow())\
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))\
    .add_extension(
        x509.SubjectAlternativeName([x509.DNSName("localhost")]),
        critical=False,
    )\
    .sign(key, hashes.SHA256())

# salva os arquivos
with open("cert/key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

with open("cert/cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("✅ Certificado criado com sucesso!")