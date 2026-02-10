"""
Quick test script to verify OpenRouter AI integration for lead scoring.
Run this to test if the AI service is working correctly.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ai_analysis_service import ai_analysis_service

def test_ai_service():
    """Test the AI service initialization and basic scoring."""
    
    print("=" * 60)
    print("OPENROUTER AI SERVICE TEST")
    print("=" * 60)
    
    # Check initialization
    print(f"\\n[OK] Provider: {ai_analysis_service.provider}")
    print(f"[OK] Model: {ai_analysis_service.model}")
    print(f"[OK] Client initialized: {ai_analysis_service.client is not None}")
    
    if not ai_analysis_service.client:
        print("\\n[ERROR] AI client not initialized!")
        return False
    
    # Test lead scoring
    print("\\n" + "-" * 60)
    print("Testing Lead Scoring...")
    print("-" * 60)
    
    test_lead = {
        "name": "John Smith",
        "title": "VP of Engineering",
        "company": "TechCorp Inc",
        "headline": "VP of Engineering at TechCorp | Building scalable systems",
        "about": "Experienced engineering leader with 10+ years in SaaS"
    }
    
    test_interactions = [
        {
            "type": "comment",
            "content": "Great insights on scaling microservices!",
            "source_url": "https://linkedin.com/post/123"
        }
    ]
    
    try:
        result = ai_analysis_service.score_lead(test_lead, test_interactions)
        
        print(f"\\n[SUCCESS] AI Scoring Successful!")
        print(f"   Score: {result.get('score')}/100")
        print(f"   Quality Tier: {result.get('quality_tier')}")
        print(f"   Reasoning: {result.get('reasoning')}")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"\\n[FAILED] AI Scoring Failed!")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error: {str(e)}")
        print("   Stack Trace:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ai_service()
    
    print("\\n" + "=" * 60)
    if success:
        print("[SUCCESS] ALL TESTS PASSED - OpenRouter is configured correctly!")
    else:
        print("[FAILED] TESTS FAILED - Check configuration and API key")
    print("=" * 60)
