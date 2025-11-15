"""
Firestore service for storing scraped website data
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from app.config import FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

class FirestoreService:
    def __init__(self):
        self.db = None
        self.init_firestore()
    
    def init_firestore(self):
        """Initialize Firestore client"""
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Initialize Firebase Admin SDK
                private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n')
                client_email = os.getenv("FIREBASE_CLIENT_EMAIL", "")
                private_key_id = os.getenv("FIREBASE_PRIVATE_KEY_ID", "")
                client_id = os.getenv("FIREBASE_CLIENT_ID", "")
                
                if not all([private_key, client_email, private_key_id, client_id]):
                    logger.warning("Firebase credentials not found, Firestore will not be available")
                    return
                
                cred_dict = {
                    "type": "service_account",
                    "project_id": FIREBASE_PROJECT_ID,
                    "private_key_id": private_key_id,
                    "private_key": private_key,
                    "client_email": client_email,
                    "client_id": client_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
                }
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            
            # Initialize Firestore client
            self.db = firestore.client()
            logger.info("✅ Firestore initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore: {str(e)}")
            self.db = None
    
    def store_scraped_website(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store scraped website data in Firestore"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "error": "Firestore client not initialized"
                }
            
            # Prepare document data
            doc_data = {
                "url": data.get("url", ""),
                "widget_id": data.get("widget_id", ""),
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "total_pages": data.get("total_pages", 0),
                "successful_pages": data.get("successful_pages", 0),
                "total_word_count": data.get("total_word_count", 0),
                "chunks_created": data.get("chunks_created", 0),
                "scraped_at": datetime.utcnow(),
                "metadata": data.get("metadata", {}),
                "status": "completed"
            }
            
            # Store in the 'scraped_websites' collection
            collection_ref = self.db.collection("scraped_websites")
            doc_ref = collection_ref.add(doc_data)
            
            logger.info(f"✅ Stored scraped website data in Firestore: {doc_ref[1].id}")
            
            return {
                "success": True,
                "message": "Scraped website data stored in Firestore successfully",
                "document_id": doc_ref[1].id,
                "collection": "scraped_websites"
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing scraped website data in Firestore: {str(e)}")
            return {
                "success": False,
                "message": "Failed to store in Firestore",
                "error": str(e)
            }
    
    def store_knowledge_chunks(self, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store knowledge chunks metadata in Firestore"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "error": "Firestore client not initialized"
                }
            
            stored_chunks = []
            collection_ref = self.db.collection("knowledge_chunks")
            
            for chunk_data in chunks_data:
                doc_data = {
                    "widget_id": chunk_data.get("widget_id", ""),
                    "vector_id": chunk_data.get("vector_id", ""),
                    "chunk_index": chunk_data.get("chunk_index", 0),
                    "content_preview": chunk_data.get("content_preview", ""),
                    "url": chunk_data.get("url", ""),
                    "title": chunk_data.get("title", ""),
                    "created_at": datetime.utcnow(),
                    "metadata": chunk_data.get("metadata", {})
                }
                
                doc_ref = collection_ref.add(doc_data)
                stored_chunks.append({
                    "document_id": doc_ref[1].id,
                    "chunk_index": chunk_data.get("chunk_index", 0),
                    "vector_id": chunk_data.get("vector_id", "")
                })
            
            logger.info(f"✅ Stored {len(stored_chunks)} knowledge chunks in Firestore")
            
            return {
                "success": True,
                "message": f"Stored {len(stored_chunks)} knowledge chunks in Firestore",
                "stored_chunks": stored_chunks,
                "collection": "knowledge_chunks"
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing knowledge chunks in Firestore: {str(e)}")
            return {
                "success": False,
                "message": "Failed to store chunks in Firestore",
                "error": str(e)
            }
    
    def get_scraped_websites(self, widget_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Retrieve scraped websites from Firestore"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "data": []
                }
            
            collection_ref = self.db.collection("scraped_websites")
            
            # Apply widget_id filter if provided
            if widget_id:
                query = collection_ref.where("widget_id", "==", widget_id)
            else:
                query = collection_ref
            
            # Order by scraped_at descending and limit results
            query = query.order_by("scraped_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = query.stream()
            websites = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                # Convert datetime to string for JSON serialization
                if "scraped_at" in data and data["scraped_at"]:
                    data["scraped_at"] = data["scraped_at"].isoformat()
                websites.append(data)
            
            return {
                "success": True,
                "message": f"Retrieved {len(websites)} scraped websites",
                "data": websites
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving scraped websites from Firestore: {str(e)}")
            return {
                "success": False,
                "message": "Failed to retrieve from Firestore",
                "error": str(e),
                "data": []
            }
    
    def store_faq(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store FAQ data in Firestore"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "error": "Firestore client not initialized"
                }
            
            # Prepare document data
            doc_data = {
                "faq_id": data.get("faq_id", ""),
                "vector_id": data.get("vector_id", ""),
                "widget_id": data.get("widget_id", ""),
                "business_id": data.get("business_id", ""),
                "title": data.get("title", ""),
                "question": data.get("question", ""),
                "answer": data.get("answer", ""),
                "tags": data.get("tags", []),
                "char_count": data.get("char_count", 0),
                "word_count": data.get("word_count", 0),
                "type": "faq",
                "created_at": datetime.utcnow(),
                "metadata": data.get("metadata", {})
            }
            
            # Store in the 'faqs' collection
            collection_ref = self.db.collection("faqs")
            doc_ref = collection_ref.add(doc_data)
            
            logger.info(f"✅ Stored FAQ in Firestore: {doc_ref[1].id}")
            
            return {
                "success": True,
                "message": "FAQ stored in Firestore successfully",
                "document_id": doc_ref[1].id,
                "collection": "faqs"
            }
            
        except Exception as e:
            logger.error(f"❌ Error storing FAQ in Firestore: {str(e)}")
            return {
                "success": False,
                "message": "Failed to store FAQ in Firestore",
                "error": str(e)
            }
    
    def get_user_conversations(self, widget_id: str, user_email: str, limit: int = 10) -> Dict[str, Any]:
        """Get all conversations for a specific user by email (secure)"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "data": []
                }
            
            logger.info(f"🔍 Fetching chat history for user: {user_email}, widget: {widget_id}")
            
            # Query conversations collection filtered by widget_id and user_email
            conversations_ref = self.db.collection("conversations")
            query = (conversations_ref
                    .where("widgetId", "==", widget_id)
                    .where("customerEmail", "==", user_email)
                    .order_by("updatedAt", direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            conversations = []
            
            for doc in docs:
                data = doc.to_dict()
                
                # Get message count
                messages_ref = doc.reference.collection("messages")
                message_count = len(list(messages_ref.stream()))
                
                # Get last message
                last_message_query = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
                last_messages = list(last_message_query.stream())
                last_message_text = ""
                
                if last_messages:
                    last_msg_data = last_messages[0].to_dict()
                    last_message_text = last_msg_data.get("text", "")
                
                conversations.append({
                    "id": doc.id,
                    "lastMessage": last_message_text,
                    "timestamp": data.get("updatedAt", datetime.utcnow()).isoformat() if hasattr(data.get("updatedAt"), 'isoformat') else str(data.get("updatedAt")),
                    "messageCount": message_count,
                    "customerName": data.get("customerName", ""),
                    "status": data.get("status", "active")
                })
            
            logger.info(f"✅ Found {len(conversations)} conversations for user: {user_email}")
            
            return {
                "success": True,
                "data": conversations
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving user conversations: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to retrieve chat history: {str(e)}",
                "data": []
            }
    
    def get_conversation_with_security(self, conversation_id: str, user_email: str) -> Dict[str, Any]:
        """Get conversation messages with security check (user must own the conversation)"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "data": None
                }
            
            logger.info(f"🔍 Fetching conversation: {conversation_id} for user: {user_email}")
            
            # Get conversation document
            conv_ref = self.db.collection("conversations").document(conversation_id)
            conv_doc = conv_ref.get()
            
            if not conv_doc.exists:
                return {
                    "success": False,
                    "message": "Conversation not found",
                    "data": None
                }
            
            conv_data = conv_doc.to_dict()
            
            # SECURITY: Verify user owns this conversation
            if conv_data.get("customerEmail") != user_email:
                logger.warning(f"⚠️ Unauthorized access attempt: {user_email} tried to access conversation of {conv_data.get('customerEmail')}")
                return {
                    "success": False,
                    "message": "Unauthorized: You can only view your own conversations",
                    "data": None
                }
            
            # Get all messages in this conversation
            messages_ref = conv_ref.collection("messages")
            messages_query = messages_ref.order_by("timestamp", direction=firestore.Query.ASCENDING)
            message_docs = messages_query.stream()
            
            messages = []
            for msg_doc in message_docs:
                msg_data = msg_doc.to_dict()
                messages.append({
                    "id": msg_doc.id,
                    "text": msg_data.get("text", ""),
                    "sender": msg_data.get("sender", "user"),
                    "timestamp": msg_data.get("timestamp", datetime.utcnow()).isoformat() if hasattr(msg_data.get("timestamp"), 'isoformat') else str(msg_data.get("timestamp")),
                    "metadata": msg_data.get("metadata", {})
                })
            
            logger.info(f"✅ Retrieved {len(messages)} messages for conversation: {conversation_id}")
            
            return {
                "success": True,
                "data": {
                    "conversation": {
                        "id": conversation_id,
                        "customerName": conv_data.get("customerName", ""),
                        "customerEmail": conv_data.get("customerEmail", ""),
                        "status": conv_data.get("status", "active")
                    },
                    "messages": messages
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error retrieving conversation: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to retrieve conversation: {str(e)}",
                "data": None
            }
    
    def delete_all_data(self, business_id: str, widget_id: str = "all") -> Dict[str, Any]:
        """Delete all Firestore data for a business or widget"""
        try:
            if not self.db:
                return {
                    "success": False,
                    "message": "Firestore not available",
                    "error": "Firestore client not initialized"
                }
            
            deleted_documents = 0
            
            # Delete from scraped_websites collection
            scraped_websites_ref = self.db.collection("scraped_websites")
            if widget_id == "all":
                query = scraped_websites_ref.where("metadata.business_id", "==", business_id)
            else:
                query = scraped_websites_ref.where("widget_id", "==", widget_id)
            
            docs = query.stream()
            for doc in docs:
                doc.reference.delete()
                deleted_documents += 1
            
            # Delete from knowledge_chunks collection
            knowledge_chunks_ref = self.db.collection("knowledge_chunks")
            if widget_id == "all":
                query = knowledge_chunks_ref.where("metadata.business_id", "==", business_id)
            else:
                query = knowledge_chunks_ref.where("widget_id", "==", widget_id)
            
            docs = query.stream()
            for doc in docs:
                doc.reference.delete()
                deleted_documents += 1
            
            # Delete from faqs collection
            faqs_ref = self.db.collection("faqs")
            if widget_id == "all":
                query = faqs_ref.where("business_id", "==", business_id)
            else:
                query = faqs_ref.where("widget_id", "==", widget_id)
            
            docs = query.stream()
            for doc in docs:
                doc.reference.delete()
                deleted_documents += 1
            
            logger.info(f"✅ Deleted {deleted_documents} documents from Firestore for business {business_id}")
            
            return {
                "success": True,
                "message": f"Successfully deleted {deleted_documents} documents from Firestore",
                "deleted_documents": deleted_documents,
                "business_id": business_id,
                "widget_id": widget_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting all Firestore data: {str(e)}")
            return {
                "success": False,
                "message": "Failed to delete data from Firestore",
                "error": str(e)
            }

    async def get_document(self, doc_path: str) -> Optional[Dict[str, Any]]:
        """Get a document from Firestore by path (format: 'collection/document_id')"""
        try:
            if not self.db:
                logger.error("Firestore not available")
                return None
            
            # Parse path: format is "collection/document_id"
            parts = doc_path.split('/')
            if len(parts) != 2:
                logger.error(f"Invalid document path format: {doc_path}. Expected format: 'collection/document_id'")
                return None
            
            collection_name, document_id = parts[0], parts[1]
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting document from Firestore: {str(e)}")
            logger.exception(e)
            return None

    async def set_document(self, doc_path: str, data: Dict[str, Any]) -> bool:
        """Set a document in Firestore by path (format: 'collection/document_id')"""
        try:
            if not self.db:
                logger.error("Firestore not available")
                return False
            
            # Parse path: format is "collection/document_id"
            parts = doc_path.split('/')
            if len(parts) != 2:
                logger.error(f"Invalid document path format: {doc_path}. Expected format: 'collection/document_id'")
                return False
            
            collection_name, document_id = parts[0], parts[1]
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.set(data)
            
            logger.info(f"✅ Document set successfully: {doc_path}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error setting document in Firestore: {str(e)}")
            return False

    def get_server_timestamp(self):
        """Get Firestore server timestamp"""
        return firestore.SERVER_TIMESTAMP

# Global service instance
firestore_service = FirestoreService()