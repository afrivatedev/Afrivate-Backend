from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from .models import Feedback, KnowledgeBaseArticle, SupportChatSession, SupportChatMessage
from .serializers import FeedbackSerializer, KnowledgeBaseArticleSerializer, SupportChatSessionSerializer, SupportChatMessageSerializer
import google.generativeai as genai
import os

# Configure Gemini AI
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

class FeedbackViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = FeedbackSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        # Users can only see their own feedback. Admins can see all (handled via admin panel).
        if getattr(self.request.user, 'is_staff', False):
            return Feedback.objects.all()
        return Feedback.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

class SupportChatSessionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SupportChatSessionSerializer
    
    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return SupportChatSession.objects.all()
        return SupportChatSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def messages(self, request, pk=None):
        session = self.get_object()
        
        # 1. Save User Message
        content = request.data.get('content')
        attachment = request.FILES.get('attachment')
        
        if not content and not attachment:
            return Response({"detail": "Message content or attachment is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = SupportChatMessage.objects.create(
            session=session,
            role='user',
            content=content or "",
            attachment=attachment
        )
        
        if session.status == 'escalated':
            # If already escalated, we just record the message. Human support will reply later.
            return Response(SupportChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)
        
        # 2. Get AI Response using Gemini
        try:
            ai_response_text = self._get_ai_response(session, content)
            
            # Check if AI decided to escalate
            if "ESCALATE" in ai_response_text:
                session.status = 'escalated'
                # Create a Feedback ticket for the escalation
                ticket = Feedback.objects.create(
                    user=session.user,
                    type='support',
                    subject=f"Escalated Chat Session #{session.id}",
                    description=f"User requested escalation or AI could not resolve. Check session #{session.id} for history.",
                    status='new',
                    priority='medium'
                )
                session.escalated_ticket = ticket
                session.save()
                
                ai_response_text = "I'm escalating this to our human support team. A ticket has been created for you."
            
            # Save Assistant Message
            SupportChatMessage.objects.create(
                session=session,
                role='assistant',
                content=ai_response_text
            )
            
        except Exception as e:
            print(f"GEMINI ERROR: {e}")
            # Fallback if AI fails
            SupportChatMessage.objects.create(
                session=session,
                role='assistant',
                content="I'm sorry, I'm having trouble connecting to my knowledge base right now. Please try again later or contact support directly."
            )
            
        # Return updated session with all messages
        return Response(SupportChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    def _get_ai_response(self, session, user_content):
        if not GENAI_API_KEY:
            return "ESCALATE"
            
        # Retrieve Knowledge Base
        kb_articles = KnowledgeBaseArticle.objects.filter(status='approved')
        kb_context = "\n\n".join([f"Q: {kb.description}\nA: {kb.solution}" for kb in kb_articles])
        
        # Retrieve previous messages for context
        history = list(session.messages.order_by('timestamp'))[-5:]
        chat_context = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
        
        prompt = f"""
You are an intelligent support assistant for Afrivate (a platform connecting skilled volunteers with organizations).
Use the following Knowledge Base to answer the user's question. 
If the answer is NOT in the knowledge base or you are unsure, you MUST reply with exactly "ESCALATE". Do not make up answers.

Knowledge Base:
{kb_context}

Recent Chat History:
{chat_context}

User's new message: {user_content}

Answer:"""
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
