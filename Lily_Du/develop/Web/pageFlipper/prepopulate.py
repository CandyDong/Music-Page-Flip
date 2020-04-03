import json

data = '''
{
"rpi_1": {"in_use":"False"},
"rpi_2": {"in_use":"False"}
}'''

obj = json.loads(data)
print(obj)

print('- ' * 20)

# Convert back to JSON for nicer printing
print(json.dumps(obj, indent=4))