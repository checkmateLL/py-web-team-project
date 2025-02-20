import bcrypt

password = b"password"
hashed_password = b"$2b$12$ULi1BxcPzFLpLnBvnduNHOWQJA1KRZ9Qa7Lmaa60RTLA38fgJzRV."  # replace with DB hash

if bcrypt.checkpw(password, hashed_password):
    print("Password is correct")
else:
    print("Password mismatch!")