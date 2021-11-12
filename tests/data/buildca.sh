mkdir -p ca/root
cd ca/root
# Generate a 8192-bit long SHA-256 RSA key for our root CA:
openssl genrsa -aes256 -out rootca.key -passout pass:test 8192
#set passphrase
# Root cert
openssl req -sha256 -new -x509 -key rootca.key -out rootca.crt --passin pass:test --days 36600
#You are about to be asked to enter information that will be incorporated into your certificate request.
#What you are about to enter is what is called a Distinguished Name or a DN.
# There are quite a few fields but you can leave some blank
# For some fields there will be a default value,
# If you enter '.', the field will be left blank.

# Create a few files where the CA will store it's serials:
touch certindex
touch certindex.attr
echo 1000 > certserial
echo 1000 > crlnumber

cat >ca.conf << 'EOF'
[ ca ]
default_ca = myca

[ crl_ext ]
issuerAltName=issuer:copy
authorityKeyIdentifier=keyid:always

[ myca ]
dir = ./
new_certs_dir = $dir
unique_subject = no
certificate = $dir/rootca.crt
database = $dir/certindex
private_key = $dir/rootca.key
serial = $dir/certserial
default_days = 36500
default_md = sha384
policy = myca_policy
x509_extensions = myca_extensions
crlnumber = $dir/crlnumber
default_crl_days = 36500

[ myca_policy ]
commonName = supplied
stateOrProvinceName = optional
countryName = supplied
emailAddress = optional
organizationName = supplied
organizationalUnitName = optional

[ myca_extensions ]
basicConstraints = critical,CA:TRUE
keyUsage = critical,any
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
keyUsage = digitalSignature,keyEncipherment,keyCertSign
extendedKeyUsage = serverAuth
subjectAltName  = ${ENV::ALTNAME}


[ v3_ca ]
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,any
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
keyUsage = digitalSignature,keyEncipherment,keyCertSign
extendedKeyUsage = serverAuth
subjectAltName  = ${ENV::ALTNAME}

EOF

#after previous

openssl genrsa -out intermediate1.key --passout pass:test 4096
openssl req -new -sha256 -key intermediate1.key -out intermediate1.csr --passin pass:test --days 36500


export ALTNAME="DNS:Inmanta Test CA"



openssl ca -batch -config ca.conf -notext -in intermediate1.csr -out intermediate1.crt  -key test

mkdir ../intermediate/
cd ../intermediate/

cp ../root/intermediate1.key .
cp ../root/intermediate1.crt .

# Create a few files where the CA will store it's serials:
touch certindex
touch certindex.attr

echo 1000 > certserial
echo 1000 > crlnumber

cat >ca-srv.conf << 'EOF'
[ ca ]
default_ca = myca

[ crl_ext ]
issuerAltName=issuer:copy
authorityKeyIdentifier=keyid:always

 [ myca ]
 dir = ./
 new_certs_dir = $dir
 unique_subject = no
 certificate = $dir/intermediate1.crt
 database = $dir/certindex
 private_key = $dir/intermediate1.key
 serial = $dir/certserial
 default_days = 36400
 default_md = sha384
 policy = myca_policy
 x509_extensions = myca_extensions
 crlnumber = $dir/crlnumber
 default_crl_days = 36400

 [ myca_policy ]
 commonName = supplied
 stateOrProvinceName = optional
 countryName = supplied
 emailAddress = optional
 organizationName = supplied
 organizationalUnitName = optional

 [ myca_extensions ]
 basicConstraints = critical,CA:FALSE
 keyUsage = critical,any
 subjectKeyIdentifier = hash
 authorityKeyIdentifier = keyid:always,issuer
 keyUsage = digitalSignature,keyEncipherment
 extendedKeyUsage = serverAuth
 subjectAltName  =  ${ENV::ALTNAME}
EOF



cat >ca-client.conf << 'EOF'
[ ca ]
default_ca = myca

[ crl_ext ]
issuerAltName=issuer:copy
authorityKeyIdentifier=keyid:always

 [ myca ]
 dir = ./
 new_certs_dir = $dir
 unique_subject = no
 certificate = $dir/intermediate1.crt
 database = $dir/certindex
 private_key = $dir/intermediate1.key
 serial = $dir/certserial
 default_days = 36300
 default_md = sha384
 policy = myca_policy
 x509_extensions = myca_extensions
 crlnumber = $dir/crlnumber
 default_crl_days = 36300

 [ myca_policy ]
 commonName = supplied
 stateOrProvinceName = optional
 countryName = supplied
 emailAddress = optional
 organizationName = supplied
 organizationalUnitName = optional

 [ myca_extensions ]
 basicConstraints = critical,CA:FALSE
 keyUsage = critical,any
 subjectKeyIdentifier = hash
 authorityKeyIdentifier = keyid:always,issuer
 keyUsage = digitalSignature,keyEncipherment
 extendedKeyUsage = clientAuth
EOF


mkdir ../enduser-certs
openssl genrsa -out ../enduser-certs/server.key  -passout pass:test 4096


openssl req -new -sha256 -key ../enduser-certs/server.key -out ../enduser-certs/server.csr -passin pass:test --days 36300



export ALTNAME="DNS:localhost, IP:127.0.0.1"
openssl ca -batch -config ca-srv.conf -notext -in ../enduser-certs/server.csr -out ../enduser-certs/server.crt -passin pass:test

cat ../root/rootca.crt intermediate1.crt > ../enduser-certs/server.chain

openssl rsa -in   ../enduser-certs/server.key  --out  ../enduser-certs/server.key.open  -passin pass:test

openssl verify -CAfile ../enduser-certs/server.chain ../enduser-certs/server.crt

