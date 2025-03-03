import tiktoken
enc = tiktoken.encoding_for_model("gpt-4") 
print(len(enc.encode('hello world')))