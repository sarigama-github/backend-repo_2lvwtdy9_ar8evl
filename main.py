import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional

from database import create_document
from schemas import Contactlead

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "DDDzn API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Lead capture endpoint
@app.post("/api/leads")
def create_lead(lead: Contactlead):
    try:
        lead_id = create_document("contactlead", lead)
        return {"status": "ok", "id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple AI assistant endpoint
class AskPayload(BaseModel):
    question: str
    email: Optional[EmailStr] = None

@app.post("/api/assistant")
def assistant(payload: AskPayload):
    q = payload.question.lower().strip()
    email = payload.email or "hello@dddzn.studio"

    knowledge = {
        "services": "We offer Exterior Design, Full Design Package, and Full Visualization, each tailored to your project's scope.",
        "pricing": "Packages start at $499 for Exterior, $2,499 for Full Design, and $3,999 for Full Visualization. Final quotes depend on scope.",
        "timeline": "Typical timelines range from 2-6 weeks depending on complexity and revisions.",
        "revisions": "All packages include structured revision rounds. Additional rounds can be added on request.",
        "software": "We primarily use Blender, Unreal Engine, and industry-standard DCC tools as needed."
    }

    for key, answer in knowledge.items():
        if key in q:
            return {"answer": answer}

    if any(word in q for word in ["how", "why", "optimize", "pipeline", "render settings", "complex", "technical", "api", "sdk", "integration"]):
        return {"answer": f"That sounds technical. For detailed guidance, please email us at {email} and our team will get back to you quickly."}

    generic = "We're DDDzn — Dreamscape, Development, & Designs. Ask about services, pricing, timelines, or send us your brief."
    return {"answer": generic}

# Stripe Checkout session creation
try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None

class CheckoutPayload(BaseModel):
    package: str
    email: Optional[EmailStr] = None

PRICE_MAP = {
    "exterior": {"name": "Exterior Design", "amount": 49900},
    "full-design": {"name": "Full Design Package", "amount": 249900},
    "full-visualization": {"name": "Full Visualization", "amount": 399900},
}

@app.post("/api/create-checkout-session")
def create_checkout_session(payload: CheckoutPayload):
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe not installed on server")

    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=400, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    pkg = PRICE_MAP.get(payload.package)
    if not pkg:
        raise HTTPException(status_code=400, detail="Unknown package")

    stripe.api_key = secret
    domain = os.getenv("FRONTEND_URL") or "http://localhost:3000"
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": pkg["name"]},
                    "unit_amount": pkg["amount"],
                },
                "quantity": 1,
            }],
            success_url=f"{domain}?status=success",
            cancel_url=f"{domain}?status=cancel",
            customer_email=payload.email,
            automatic_tax={"enabled": False},
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
