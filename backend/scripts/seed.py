import asyncio
from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.auth.jwt_handler import get_password_hash
from sqlalchemy import select

async def seed_database():
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == "admin@autoclip.ai"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                email="admin@autoclip.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
        
        # Check if editor exists
        result = await db.execute(select(User).where(User.email == "editor@autoclip.ai"))
        editor = result.scalar_one_or_none()
        
        if not editor:
            editor = User(
                email="editor@autoclip.ai",
                hashed_password=get_password_hash("editor123"),
                full_name="Editor",
                role=UserRole.EDITOR,
                is_active=True
            )
            db.add(editor)
        
        await db.commit()
        print("Database seeded successfully!")
        print("Admin: admin@autoclip.ai / admin123")
        print("Editor: editor@autoclip.ai / editor123")

if __name__ == "__main__":
    asyncio.run(seed_database())
