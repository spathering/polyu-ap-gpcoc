import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .errors import DomainError
ROOT=Path(__file__).resolve().parents[3]
SCHEMAS=json.loads((ROOT/"contracts/messages.json").read_text(encoding="utf-8"))

def check(kind,data):
    try: Draft202012Validator(SCHEMAS[kind]).validate(data)
    except Exception as e: raise DomainError("INPUT_INVALID",str(e)) from e

def input_schema(inputs):
    types={"amount":{"type":"integer","minimum":0,"maximum":1000000},"quantity":{"type":"integer","minimum":1,"maximum":1000000},
           "text":{"type":"string","maxLength":1000},"choice":{"type":"boolean"}}
    props={name:types.get(kind,{"type":"string","minLength":1,"maxLength":100}) for name,kind in inputs.items()}
    return {"type":"object","properties":props,"required":list(props),"additionalProperties":False}

MODELS=json.loads((ROOT/'contracts/models.json').read_text(encoding='utf-8'))
OPERATIONS=json.loads((ROOT/'contracts/operations.json').read_text(encoding='utf-8'))
def validate_model(kind,value):
    try:Draft202012Validator(MODELS[kind]).validate(value)
    except Exception:raise DomainError('INPUT_INVALID')
def validate_operation(op,args):
    if op not in OPERATIONS:raise DomainError('UNKNOWN_OPERATION')
    try:Draft202012Validator(OPERATIONS[op]).validate(args)
    except Exception:raise DomainError('INPUT_INVALID')
