import os
import asyncio
from typing import Optional, Tuple
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update


class TelegramHITL:
    """Human-in-the-loop approval workflow via Telegram."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        collect_feedback: bool = True,
    ):
        """
        Initialize Telegram HITL client.
        
        Args:
            bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (defaults to TELEGRAM_CHAT_ID env var)
            collect_feedback: Whether to collect feedback when posts are rejected
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.collect_feedback = collect_feedback
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment or provided")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set in environment or provided")
        
        self.chat_id_int = int(self.chat_id)
        
        # State for approval flow
        self.pending_post = None
        self.pending_image_url = None
        self.pending_message_has_photo = False
        self.decision_result = None
        self.rejection_reason = None
        self.waiting_for_reason = False
        self.decision_event = asyncio.Event()
        self.app = None
    
    async def send_post_for_approval(
        self,
        post_text: str,
        image_url: Optional[str] = None,
        timeout: float = 300.0,  # 5 minutes default timeout
    ) -> Tuple[str, Optional[str]]:
        """
        Send a post for human approval via Telegram.
        
        Args:
            post_text: The post content to approve
            image_url: Optional URL of image to preview
            timeout: Maximum time to wait for approval (seconds)
        
        Returns:
            Tuple of (decision, rejection_reason)
            - decision: 'approve' or 'reject'
            - rejection_reason: None if approved, feedback text if rejected
        """
        # Reset state
        self.pending_post = post_text
        self.pending_image_url = image_url
        self.pending_message_has_photo = False
        self.decision_result = None
        self.rejection_reason = None
        self.waiting_for_reason = False
        self.decision_event.clear()
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                InlineKeyboardButton("❌ Reject", callback_data="reject"),
            ]
        ])
        
        # Build message text
        message_text = f"📝 New Post for Approval\n\n{post_text}\n\n"
        message_text += f"Characters: {len(post_text)}"
        if image_url:
            message_text += "\n🖼️ Includes image"
        
        # Send message
        bot = Bot(token=self.bot_token)
        
        if image_url:
            # Send image with caption and buttons
            await bot.send_photo(
                chat_id=self.chat_id_int,
                photo=image_url,
                caption=message_text,
                reply_markup=keyboard,
            )
            self.pending_message_has_photo = True
        else:
            # Send text message with buttons
            await bot.send_message(
                chat_id=self.chat_id_int,
                text=message_text,
                reply_markup=keyboard,
            )
            self.pending_message_has_photo = False
        
        print("📱 Post sent to Telegram. Waiting for approval...")
        
        # Set up handlers - use a wrapper to ensure proper error handling
        async def handle_button_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await self._handle_button_click(update, context)
        
        async def handle_text_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await self._handle_text_feedback(update, context)
        
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(CallbackQueryHandler(handle_button_wrapper))
        
        if self.collect_feedback:
            self.app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_wrapper)
            )
        
        # Start polling
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Wait for decision with timeout
            try:
                await asyncio.wait_for(self.decision_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print("⏱️ Approval timeout. Defaulting to reject.")
                self.decision_result = "reject"
                self.rejection_reason = "Timeout: No response received"
        except Exception as e:
            print(f"Error in Telegram polling: {e}")
            import traceback
            traceback.print_exc()
            if not self.decision_event.is_set():
                self.decision_result = "reject"
                self.rejection_reason = f"Error in Telegram workflow: {str(e)}"
                self.decision_event.set()
        finally:
            # Cleanup
            try:
                if self.app and self.app.updater:
                    await self.app.updater.stop()
                if self.app:
                    await self.app.stop()
                    await self.app.shutdown()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                self.app = None
        
        return self.decision_result or "reject", self.rejection_reason
    
    async def _handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks (Approve/Reject)."""
        try:
            query = update.callback_query
            if not query:
                print("Warning: No callback_query in update")
                return
            
            print(f"📥 Button clicked: {query.data}")
            await query.answer()
            
            if query.data == "approve":
                self.decision_result = "approve"
                status_text = f"✅ APPROVED\n\n{self.pending_post}"
                if self.pending_image_url:
                    status_text += "\n\n🖼️ Image will be included."
                try:
                    # Use edit_message_caption for photo messages, edit_message_text for text messages
                    if self.pending_message_has_photo:
                        await query.edit_message_caption(caption=status_text)
                    else:
                        await query.edit_message_text(status_text)
                except Exception as e:
                    # If editing fails (e.g., message too long), try to send new message
                    print(f"Warning: Could not edit message: {e}")
                    await context.bot.send_message(
                        chat_id=self.chat_id_int,
                        text=status_text
                    )
                self.decision_event.set()
            
            elif query.data == "reject":
                self.decision_result = "reject"
                reject_text = "❌ REJECTED\n\n"
                if self.collect_feedback:
                    reject_text += (
                        "Please reply with the reason for rejection.\n"
                        "This feedback helps improve future posts.\n\n"
                        "Examples: 'Too promotional', 'Wrong tone', 'Needs more context'"
                    )
                else:
                    reject_text += f"{self.pending_post[:100]}..."
                
                try:
                    # Use edit_message_caption for photo messages, edit_message_text for text messages
                    if self.pending_message_has_photo:
                        await query.edit_message_caption(caption=reject_text)
                    else:
                        await query.edit_message_text(reject_text)
                except Exception as e:
                    print(f"Warning: Could not edit message: {e}")
                    await context.bot.send_message(
                        chat_id=self.chat_id_int,
                        text=reject_text
                    )
                
                if self.collect_feedback:
                    self.waiting_for_reason = True
                else:
                    self.decision_event.set()
        except Exception as e:
            print(f"Error handling button click: {e}")
            import traceback
            traceback.print_exc()
            # Try to set the event anyway to avoid hanging
            if not self.decision_event.is_set():
                self.decision_result = "reject"
                self.rejection_reason = f"Error processing approval: {str(e)}"
                self.decision_event.set()
    
    async def _handle_text_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text feedback when post is rejected."""
        if not self.waiting_for_reason:
            return
        
        self.rejection_reason = update.message.text
        self.waiting_for_reason = False
        await update.message.reply_text(
            f"📝 Feedback recorded!\n\nReason: {self.rejection_reason}"
        )
        self.decision_event.set()
    
    async def send_notification(self, message: str):
        """Send a simple notification message (no approval needed)."""
        bot = Bot(token=self.bot_token)
        await bot.send_message(
            chat_id=self.chat_id_int,
            text=message,
        )


async def wait_for_approval(
    post_text: str,
    image_url: Optional[str] = None,
    collect_feedback: bool = True,
    timeout: float = 300.0,
) -> Tuple[str, Optional[str]]:
    """
    Convenience function to send a post for approval.
    
    Args:
        post_text: The post content to approve
        image_url: Optional URL of image to preview
        collect_feedback: Whether to collect feedback when rejected
        timeout: Maximum time to wait for approval (seconds)
    
    Returns:
        Tuple of (decision, rejection_reason)
    """
    hitl = TelegramHITL(collect_feedback=collect_feedback)
    return await hitl.send_post_for_approval(post_text, image_url, timeout)
