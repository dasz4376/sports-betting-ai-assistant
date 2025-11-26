"""
Run Continuous Learning Analysis
Analyzes completed games and triggers retraining when needed
"""

import sys
from database import SessionLocal
from services.continuous_learning import ContinuousLearning

def main():
    print("\n" + "="*80)
    print("NFL BETTING AI - CONTINUOUS LEARNING SYSTEM")
    print("="*80 + "\n")
    
    db = SessionLocal()
    try:
        cl = ContinuousLearning(db)
        
        # Analyze last week's games
        print("Step 1: Analyzing completed games from last week...")
        result = cl.analyze_completed_games(weeks_back=1)
        
        if result["predictions_updated"] > 0:
            print(f"\n{'='*80}")
            print("Step 2: Generating accuracy report...")
            print(f"{'='*80}\n")
            
            report = cl.get_accuracy_report()
            
            print(f"OVERALL ACCURACY REPORT")
            print(f"{'-'*80}")
            print(f"Total Validated Predictions: {report['total_predictions']}")
            print(f"Accurate Predictions: {report['accurate_predictions']}")
            print(f"Overall Accuracy: {report['overall_accuracy']:.1f}%")
            
            print(f"\nTop Performing Prop Types:")
            print(f"{'-'*80}")
            
            sorted_props = sorted(
                report['by_prop_type'].items(),
                key=lambda x: x[1]['accuracy_pct'],
                reverse=True
            )[:5]
            
            for prop_type, stats in sorted_props:
                print(f"{prop_type:25} | {stats['accuracy_pct']:5.1f}% accurate | Avg Error: {stats['avg_error']:.2f}")
            
            print(f"\n{'='*80}")
            print("✓ CONTINUOUS LEARNING COMPLETE")
            print(f"{'='*80}\n")
        else:
            print("\nNo predictions to validate from completed games.")
            print("Predictions are only stored when using the betting engine.")
            print("\nTo generate predictions, run: py run_betting_ai.py")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

