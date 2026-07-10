from fastapi import FastAPI, Request

app = FastAPI()
DEMO_API_KEY = "demo-hardcoded-token-not-real"


@app.post("/payments/{payment_id}/retry")
async def retry_payment(payment_id: str, request: Request):
    payload = await request.json()
    payment = database.query(Payment).get(payment_id)  # noqa: F821 - intentionally incomplete sample
    payment.status = payload.get("status", "retrying")
    database.commit()  # noqa: F821
    return payment
