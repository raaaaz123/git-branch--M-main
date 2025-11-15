"""
Credit management service for message credits
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from app.services.firestore_service import FirestoreService

logger = logging.getLogger(__name__)

class CreditService:
    def __init__(self):
        self.firestore_service = FirestoreService()
        self.db = self.firestore_service.db

    async def get_agent_owner(self, agent_id: str) -> Optional[str]:
        """
        Get the owner (workspace owner or user) of an agent
        Returns the user ID of the agent's workspace owner
        """
        try:
            if not self.db:
                logger.error("Firestore not available")
                return None

            # Get agent document
            agent_ref = self.db.collection('agents').document(agent_id)
            agent_doc = agent_ref.get()

            if not agent_doc.exists:
                logger.error(f"Agent {agent_id} not found")
                return None

            agent_data = agent_doc.to_dict()
            workspace_id = agent_data.get('workspaceId')

            if not workspace_id:
                logger.error(f"Agent {agent_id} has no workspaceId")
                return None

            # Get workspace document to find the owner
            workspace_ref = self.db.collection('workspaces').document(workspace_id)
            workspace_doc = workspace_ref.get()

            if not workspace_doc.exists:
                logger.error(f"Workspace {workspace_id} not found")
                return None

            workspace_data = workspace_doc.to_dict()
            owner_id = workspace_data.get('ownerId')

            if not owner_id:
                # If no ownerId, try to find workspace members with owner role
                members_query = self.db.collection('workspace_members') \
                    .where('workspaceId', '==', workspace_id) \
                    .where('role', '==', 'owner') \
                    .limit(1)

                members_docs = list(members_query.stream())
                if members_docs:
                    member_data = members_docs[0].to_dict()
                    owner_id = member_data.get('userId')

            if not owner_id:
                logger.error(f"Could not find owner for workspace {workspace_id}")
                return None

            logger.info(f"Found owner {owner_id} for agent {agent_id}")
            return owner_id

        except Exception as e:
            logger.error(f"Error getting agent owner: {str(e)}")
            return None

    async def get_workspace_credits(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get credit information for a workspace
        Returns dict with messageCredits, messageCreditsUsed, and creditsRemaining
        """
        try:
            if not self.db:
                return {
                    "success": False,
                    "error": "Firestore not available",
                    "messageCredits": 0,
                    "messageCreditsUsed": 0,
                    "creditsRemaining": 0
                }

            workspace_ref = self.db.collection('workspaces').document(workspace_id)
            workspace_doc = workspace_ref.get()

            if not workspace_doc.exists:
                logger.error(f"Workspace {workspace_id} not found")
                return {
                    "success": False,
                    "error": "Workspace not found",
                    "messageCredits": 0,
                    "messageCreditsUsed": 0,
                    "creditsRemaining": 0
                }

            workspace_data = workspace_doc.to_dict()
            subscription = workspace_data.get('subscription', {})

            # Get base credits from subscription plan
            message_credits = subscription.get('messageCredits', 100)
            message_credits_used = subscription.get('messageCreditsUsed', 0)

            # Add extra monthly credits if any
            extra_credits = subscription.get('extraCredits', {}).get('amount', 0)
            total_credits = message_credits + extra_credits

            credits_remaining = max(0, total_credits - message_credits_used)

            return {
                "success": True,
                "messageCredits": total_credits,
                "messageCreditsUsed": message_credits_used,
                "creditsRemaining": credits_remaining,
                "hasCredits": credits_remaining > 0,
                "autoRecharge": subscription.get('autoRecharge', {})
            }

        except Exception as e:
            logger.error(f"Error getting workspace credits: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "messageCredits": 0,
                "messageCreditsUsed": 0,
                "creditsRemaining": 0
            }

    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """
        Get credit information for a user (legacy - for backward compatibility)
        Returns dict with messageCredits, messageCreditsUsed, and creditsRemaining
        """
        try:
            if not self.db:
                return {
                    "success": False,
                    "error": "Firestore not available",
                    "messageCredits": 0,
                    "messageCreditsUsed": 0,
                    "creditsRemaining": 0
                }

            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                logger.error(f"User {user_id} not found")
                return {
                    "success": False,
                    "error": "User not found",
                    "messageCredits": 0,
                    "messageCreditsUsed": 0,
                    "creditsRemaining": 0
                }

            user_data = user_doc.to_dict()
            message_credits = user_data.get('messageCredits', 0)
            message_credits_used = user_data.get('messageCreditsUsed', 0)
            credits_remaining = max(0, message_credits - message_credits_used)

            return {
                "success": True,
                "messageCredits": message_credits,
                "messageCreditsUsed": message_credits_used,
                "creditsRemaining": credits_remaining,
                "hasCredits": credits_remaining > 0
            }

        except Exception as e:
            logger.error(f"Error getting user credits: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "messageCredits": 0,
                "messageCreditsUsed": 0,
                "creditsRemaining": 0
            }

    async def check_and_deduct_credit(self, agent_id: str) -> Dict[str, Any]:
        """
        Check if the agent's workspace has credits and deduct one if available
        Uses workspace-based subscription credits
        Returns dict with success status and remaining credits
        """
        try:
            if not self.db:
                return {
                    "success": False,
                    "error": "Firestore not available",
                    "creditsRemaining": 0
                }

            # Get agent document to find workspace
            agent_ref = self.db.collection('agents').document(agent_id)
            agent_doc = agent_ref.get()

            if not agent_doc.exists:
                logger.error(f"Agent {agent_id} not found")
                return {
                    "success": False,
                    "error": "Agent not found",
                    "creditsRemaining": 0
                }

            agent_data = agent_doc.to_dict()
            workspace_id = agent_data.get('workspaceId')

            if not workspace_id:
                logger.error(f"Agent {agent_id} has no workspaceId")
                return {
                    "success": False,
                    "error": "Agent has no workspace",
                    "creditsRemaining": 0
                }

            # Get workspace credits
            credit_info = await self.get_workspace_credits(workspace_id)
            if not credit_info["success"]:
                return {
                    "success": False,
                    "error": credit_info.get("error", "Error getting credits"),
                    "creditsRemaining": 0
                }

            # Check if credits available
            if not credit_info["hasCredits"]:
                logger.warning(f"Workspace {workspace_id} has no credits remaining")
                return {
                    "success": False,
                    "error": "No credits remaining",
                    "creditsRemaining": 0,
                    "messageCredits": credit_info["messageCredits"],
                    "messageCreditsUsed": credit_info["messageCreditsUsed"]
                }

            # Deduct credit atomically from workspace subscription
            workspace_ref = self.db.collection('workspaces').document(workspace_id)
            workspace_ref.update({
                'subscription.messageCreditsUsed': firestore.Increment(1),
                'updatedAt': firestore.SERVER_TIMESTAMP
            })

            new_credits_used = credit_info["messageCreditsUsed"] + 1
            new_credits_remaining = credit_info["messageCredits"] - new_credits_used

            logger.info(f"Deducted 1 credit from workspace {workspace_id}. Remaining: {new_credits_remaining}")

            # Check auto-recharge threshold
            auto_recharge = credit_info.get("autoRecharge", {})
            if auto_recharge.get("enabled") and new_credits_remaining <= auto_recharge.get("threshold", 0):
                logger.info(f"⚡ Auto-recharge threshold reached for workspace {workspace_id}")

                # Trigger auto-recharge asynchronously
                try:
                    from app.services.auto_recharge_service import auto_recharge_service
                    recharge_amount = auto_recharge.get("amount", 1000)
                    recharge_result = await auto_recharge_service.trigger_auto_recharge(
                        workspace_id,
                        recharge_amount
                    )

                    if recharge_result.get("success"):
                        logger.info(f"✅ Auto-recharge triggered successfully for workspace {workspace_id}")
                        # Send notification email
                        await auto_recharge_service.send_auto_recharge_notification(
                            workspace_id,
                            recharge_amount,
                            recharge_result.get("amount", 0)
                        )
                    else:
                        logger.warning(f"⚠️ Auto-recharge failed for workspace {workspace_id}: {recharge_result.get('error')}")
                except Exception as e:
                    logger.error(f"❌ Error triggering auto-recharge: {str(e)}")
                    # Don't fail the credit deduction if auto-recharge fails

            return {
                "success": True,
                "creditsRemaining": new_credits_remaining,
                "messageCredits": credit_info["messageCredits"],
                "messageCreditsUsed": new_credits_used,
                "workspaceId": workspace_id
            }

        except Exception as e:
            logger.error(f"Error checking/deducting credit: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "creditsRemaining": 0
            }

# Global instance
credit_service = CreditService()
