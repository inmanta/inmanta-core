# Password hashing algorithm

* Status: accepted
* Date: 2023-03-03


## Context and Problem Statement

When we support users that are managed in our database we need to hash the passwords used. This hash needs to be safe and follow
current best practices. OWASP is a trusted source of [information](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#password-hashing-algorithms
) for this.

## Considered Options

* Use hashing built-in python
* Use argon2id recommended by OWASP
* Use bcrypt recommended as second choice by OWASP

## Decision Outcome

We decided to use argon2id. Python itself does not provide any algorithm recommended by OWASP. argon2id is the password hashing
algorithm used by PyNACL which is python binding for libsodium. libsodium is designed and implemented by the absolute top 
authorities in the crypto world

### Positive Consequences

* Use the OWASP recommended hash, provided by a very highly regarded python library.

### Negative Consequences

* We have another external dependency.

## Pros and Cons of the Options

### Use built-in python hashing

The simple option is to use a hash built-in into python.

* Good, because there is no extra dependency
* Bad, because we would not use a hash recommended by OWASP
* Very bad, because we would be building our own password hashing based on generic hashing. We would not be talking things like
  salting and computational complexity into account.

### Use argon2id with pynacl

https://pynacl.readthedocs.io/en/latest/password_hashing/

* Good, because it is the recommended method by OWASP
* Good, because pynacl offers password hashing that uses argon2id in the back.
* Good, because pynacl uses libsodium. libsodium is designed and implemented by some of the biggest names in the crypto world.
* Bad, because it introduces another dependency. However, it is already a dep when using the yang handler (through paramiko).
  pyncal also offers other primitives that we might use in the future.

### Use bcrypt

https://github.com/pyca/bcrypt/

* Good, because it is the second best recommended method by OWASP
* Bad, because it requires an additional library. However, it is already a dep when using the yang handler (through paramiko).

 