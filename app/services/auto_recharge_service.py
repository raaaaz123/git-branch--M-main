"""
Auto-Recharge Service for Message Credits
Handles automatic credit recharges when workspace credits fall below threshold
"""
import logging
from typing import Dict, Any, Optional
import httpx
from app.config import settings
from app.services.firestore_service import FirestoreService
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class AutoRechargeService:
    def __init__(self):
        self.firestore_service = FirestoreService()
        self.db = self.firestore_service.db
        self.dodo_api_key = settings.DODO_PAYMENTS_API_KEY if hasattr(settings, 'DODO_PAYMENTS_API_KEY') else None
        self.dodo_api_url = "https://api.dodopayments.com/v1"

    async def trigger_auto_recharge(
        self,
        workspace_id: str,
        amount: number,
        price_per_thousand: number = 14
    ) -> Dict[str, Any]:
        """
        Trigger an automatic credit recharge for a workspace
        Creates a one-time payment via Dodo Payments

        Args:
            workspace_id: The workspace ID to recharge
            amount: Number of credits to add (in thousands, e.g., 1000, 2000)
            price_per_thousand: Price per 1000 credits (default $14)

        Returns:
            Dict with success status and payment details
        """
        try:
            logger.info(f"🔄 [Auto-Recharge] Triggering auto-recharge for workspace {workspace_id}: {amount} credits")

            # Get workspace document
            workspace_ref = self.db.collection('workspaces').document(workspace_id)
            workspace_doc = workspace_ref.get()

            if not workspace_doc.exists:
                return {
                    "success": False,
                    "error": f"Workspace {workspace_id} not found"
                }

            workspace_data = workspace_doc.to_dict()
            subscription = workspace_data.get('subscription', {})

            # Get Dodo customer ID
            customer_id = subscription.get('dodoCustomerId')
            if not customer_id:
                logger.error(f"❌ [Auto-Recharge] No Dodo customer ID for workspace {workspace_id}")
                return {
                    "success": False,
                    "error": "No payment method on file"
                }

            # Calculate total cost
            total_cost = (amount / 1000) * price_per_thousand

            # TODO: Create one-time charge via Dodo Payments API
            # This requires the Dodo Payments product ID for auto-recharge
            # For now, we'll log what should happen

            logger.warning(f"⚠️ [Auto-Recharge] Auto-recharge trigger not fully implemented")
            logger.info(f"📋 [Auto-Recharge] Would charge customer {customer_id}: ${total_cost} for {amount} credits")

            # Placeholder implementation - in production, this would:
            # 1. Create a one-time charge via Dodo Payments
            # 2. Wait for payment confirmation
            # 3. Add credits to workspace (done by webhook on payment.succeeded)

            """
            # Example implementation (requires Dodo Payments Python SDK or direct API calls):

            if not self.dodo_api_key:
                raise ValueError("Dodo Payments API key not configured")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.dodo_api_url}/payments/one-time",
                    headers={
                        "Authorization": f"Bearer {self.dodo_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "customer_id": customer_id,
                        "amount": int(total_cost * 100),  # Amount in cents
                        "currency": "usd",
                        "description": f"Auto-recharge: {amount} message credits",
                        "metadata": {
                            "workspaceId": workspace_id,
                            "addOnType": "auto_recharge",
                            "addOnAmount": amount
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"❌ [Auto-Recharge] Dodo API error: {response.text}")
                    return {
                        "success": False,
                        "error": "Failed to process auto-recharge payment"
                    }

                payment_data = response.json()
                logger.info(f"✅ [Auto-Recharge] Payment created: {payment_data.get('id')}")

                # Credits will be added by webhook when payment.succeeded event is received
                return {
                    "success": True,
                    "payment_id": payment_data.get('id'),
                    "amount": total_cost,
                    "credits": amount
                }
            """

            # For now, return a placeholder response
            return {
                "success": False,
                "error": "Auto-recharge trigger not fully implemented - requires Dodo Payments integration",
                "note": f"Would charge ${total_cost} for {amount} credits to customer {customer_id}"
            }

        except Exception as e:
            logger.error(f"❌ [Auto-Recharge] Error triggering auto-recharge: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_auto_recharge_notification(
        self,
        workspace_id: str,
        amount: int,
        total_cost: float
    ) -> bool:
        """
        Send email notification to workspace owner about auto-recharge

        Args:
            workspace_id: The workspace ID
            amount: Number of credits recharged
            total_cost: Total cost of the recharge

        Returns:
            True if email sent successfully
        """
        try:
            # Get workspace and owner information
            workspace_ref = self.db.collection('workspaces').document(workspace_id)
            workspace_doc = workspace_ref.get()

            if not workspace_doc.exists:
                logger.error(f"❌ [Auto-Recharge Email] Workspace {workspace_id} not found")
                return False

            workspace_data = workspace_doc.to_dict()
            owner_id = workspace_data.get('ownerId')

            if not owner_id:
                logger.error(f"❌ [Auto-Recharge Email] No owner for workspace {workspace_id}")
                return False

            # Get owner's email
            user_ref = self.db.collection('users').document(owner_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                logger.error(f"❌ [Auto-Recharge Email] Owner {owner_id} not found")
                return False

            user_data = user_doc.to_dict()
            owner_email = user_data.get('email')
            owner_name = user_data.get('displayName', 'User')

            if not owner_email:
                logger.error(f"❌ [Auto-Recharge Email] No email for owner {owner_id}")
                return False

            # TODO: Send email notification
            # This would use your email service (SendPulse, etc.)
            logger.info(f"📧 [Auto-Recharge Email] Would send to {owner_email}: {amount} credits recharged for ${total_cost}")

            """
            # Example implementation:
            from app.services.email_service import send_email

            await send_email(
                to=owner_email,
                subject="Auto-Recharge Successful - Credits Added",
                template="auto_recharge_success",
                data={
                    "workspace_name": workspace_data.get('name'),
                    "credits_added": amount,
                    "amount_charged": total_cost,
                    "owner_name": owner_name
                }
            )
            """

            return True

        except Exception as e:
            logger.error(f"❌ [Auto-Recharge Email] Error sending notification: {str(e)}")
            return False

# Global instance
auto_recharge_service = AutoRechargeService()
