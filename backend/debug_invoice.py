import asyncio
from app.core.database import get_db

async def main():
    db = get_db()

    invoice = await db.invoices.find_one(
        {"number": "INV-00004"},
        {"_id": 0}
    )

    print("========== INVOICE ==========")
    print(invoice)

    if invoice and invoice.get("client_id"):
        client = await db.clients.find_one(
            {"id": invoice["client_id"]},
            {"_id": 0}
        )

        print()
        print("========== CLIENT ==========")
        print(client)

asyncio.run(main())
