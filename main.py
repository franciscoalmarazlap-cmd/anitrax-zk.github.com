from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json
import hashlib
import os
import uuid

app = FastAPI(title="ANITRAX ZK Proof Server")

ZK_DIR = r"C:\Users\Francisco Almaraz\anitrax-zk"
WASM_PATH = os.path.join(ZK_DIR, "solvencia_js", "solvencia.wasm")
ZKEY_PATH = os.path.join(ZK_DIR, "solvencia_final.zkey")
WITNESS_GEN_SCRIPT = os.path.join(ZK_DIR, "solvencia_js", "generate_witness.js")


class ProofRequest(BaseModel):
    saldo: float
    monto: float


class ProofResponse(BaseModel):
    valido: bool
    proof_hash: str
    monto_publico: float
    mensaje: str


@app.post("/generar-prueba", response_model=ProofResponse)
def generar_prueba(req: ProofRequest):
    if req.monto > req.saldo:
        raise HTTPException(
            status_code=400,
            detail="El monto excede el saldo disponible — no se puede generar prueba valida"
        )

    work_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(ZK_DIR, f"_tmp_{work_id}")
    os.makedirs(work_dir, exist_ok=True)

    input_path = os.path.join(work_dir, "input.json")
    witness_path = os.path.join(work_dir, "witness.wtns")
    proof_path = os.path.join(work_dir, "proof.json")
    public_path = os.path.join(work_dir, "public.json")

    try:
        with open(input_path, "w") as f:
            json.dump({
                "saldo": str(int(req.saldo)),
                "monto": str(int(req.monto))
            }, f)

        result = subprocess.run(
            ["node", WITNESS_GEN_SCRIPT, WASM_PATH, input_path, witness_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Error generando witness: {result.stderr}")

        result = subprocess.run(
            ["snarkjs", "groth16", "prove", ZKEY_PATH, witness_path, proof_path, public_path],
            capture_output=True, text=True, timeout=30, shell=True
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Error generando prueba: {result.stderr}")

        with open(proof_path, "rb") as f:
            proof_bytes = f.read()
        proof_hash = hashlib.sha256(proof_bytes).hexdigest()

        return ProofResponse(
            valido=True,
            proof_hash=proof_hash,
            monto_publico=req.monto,
            mensaje="Prueba ZK generada correctamente. El saldo real nunca fue transmitido."
        )

    finally:
        for f in [input_path, witness_path]:
            if os.path.exists(f):
                os.remove(f)


@app.get("/")
def health():
    return {"status": "ANITRAX ZK Proof Server activo"}