"""
Simple test to demonstrate state behavior in pipeline nodes.
Testing what happens when nodes return partial vs full state.
"""

# Simulate the chunking node behavior
def chunking_node_current_implementation(state):
    """This is how the chunking node currently works - returns only specific fields."""
    print("=== CHUNKING NODE (Current Implementation) ===")
    print(f"Input state: {state}")
    
    # Do some work
    chunks = ["chunk1", "chunk2", "chunk3"]
    
    # Return only specific fields (this is the problem)
    result = {
        "chunks": chunks,
        "status": "chunked"
    }
    
    print(f"Output state: {result}")
    return result


def chunking_node_correct_implementation(state):
    """This is how the chunking node SHOULD work - preserves all state."""
    print("=== CHUNKING NODE (Correct Implementation) ===")
    print(f"Input state: {state}")
    
    # Do some work
    chunks = ["chunk1", "chunk2", "chunk3"]
    
    # Return full state with new fields (this preserves everything)
    result = {
        **state,  # Keep everything from input
        "chunks": chunks,
        "status": "chunked"
    }
    
    print(f"Output state: {result}")
    return result


def test_state_behavior():
    """Test both approaches to see the difference."""
    
    # Initial pipeline state (what we start with)
    initial_state = {
        "document_id": "test_doc_1",
        "user_id": "test_user",
        "document_text": "docs/example.md",
        "classification": "contract",
        "previous_status": "initialized"
    }
    
    print("🔥 TESTING STATE BEHAVIOR")
    print("=" * 60)
    print(f"INITIAL STATE: {initial_state}")
    print()
    
    # Test 1: Current (broken) implementation
    print("TEST 1: Current Implementation (What's happening now)")
    print("-" * 55)
    result1 = chunking_node_current_implementation(initial_state)
    print(f"❌ LOST FIELDS: document_id, user_id, document_text, classification")
    print(f"✅ KEPT FIELDS: chunks, status")
    print()
    
    # Test 2: Correct implementation  
    print("TEST 2: Correct Implementation (What should happen)")
    print("-" * 55)
    result2 = chunking_node_correct_implementation(initial_state)
    print(f"✅ KEPT ALL FIELDS: document_id, user_id, document_text, classification, chunks, status")
    print()
    
    # Show the impact on next node
    print("IMPACT ON NEXT NODE:")
    print("-" * 25)
    print("If next node tries to access document_id...")
    
    print(f"Current approach: result1.get('document_id') = {result1.get('document_id')}")  # None!
    print(f"Correct approach: result2.get('document_id') = {result2.get('document_id')}")  # Works!
    
    return result1, result2


def demonstrate_pipeline_break():
    """Show how this breaks a multi-step pipeline."""
    print("\n" + "=" * 60)
    print("🚨 DEMONSTRATING PIPELINE BREAK")
    print("=" * 60)
    
    initial_state = {
        "document_id": "test_doc_1",
        "user_id": "test_user",
        "document_text": "docs/example.md"
    }
    
    print(f"Starting state: {initial_state}")
    print()
    
    # Step 1: Chunking (current broken implementation)
    step1_result = {
        "chunks": ["chunk1", "chunk2"],
        "status": "chunked"
    }
    print(f"After chunking: {step1_result}")
    print("❌ Lost: document_id, user_id, document_text")
    print()
    
    # Step 2: Classification tries to access document_text
    print("Step 2: Classification node tries to run...")
    document_text = step1_result.get("document_text")  # None!
    document_id = step1_result.get("document_id")      # None!
    
    if not document_text or not document_id:
        print("❌ CLASSIFICATION FAILS: Missing document_text or document_id")
        print(f"   document_text = {document_text}")
        print(f"   document_id = {document_id}")
    else:
        print("✅ Classification would succeed")


if __name__ == "__main__":
    # Run the tests
    test_state_behavior()
    demonstrate_pipeline_break()