"""
Generate pipeline diagram for video summarization.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Create figure
fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis('off')

# Title
ax.text(5, 11.5, 'Automatic Video Summarization Pipeline', 
        fontsize=20, fontweight='bold', ha='center')

# Define colors
color_input = '#E8F4F8'
color_process = '#B8E6F0'
color_feature = '#88D8E8'
color_analysis = '#F0D8B8'
color_output = '#F0B8C8'

# Helper function to create boxes
def create_box(ax, x, y, width, height, text, color, fontsize=11):
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                         boxstyle="round,pad=0.1", 
                         edgecolor='black', facecolor=color, linewidth=2)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, 
            fontweight='bold', wrap=True)

# Helper function to create arrows
def create_arrow(ax, x1, y1, x2, y2, label=''):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', mutation_scale=20, 
                           linewidth=2, color='black')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x + 0.3, mid_y, label, fontsize=9, style='italic')

# 1. Input
create_box(ax, 5, 10, 2, 0.7, 'Input Video', color_input)
create_arrow(ax, 5, 9.65, 5, 9.2)

# 2. Load Video
create_box(ax, 5, 8.8, 2.5, 0.7, '1. Load Video\n& Sample Frames', color_process)
create_arrow(ax, 5, 8.45, 5, 8.0)

# 3. Feature Extraction (parallel)
y_feature = 7.3
create_box(ax, 2.5, y_feature, 2.2, 0.9, 
          '2a. HSV Color\nHistogram\n(8×8×8 bins)', color_feature, 10)
create_box(ax, 7.5, y_feature, 2.2, 0.9, 
          '2b. Edge\nHistogram\n(Canny + bins)', color_feature, 10)

# Arrows from Load Video to features
create_arrow(ax, 4.5, 8.0, 2.8, y_feature + 0.45)
create_arrow(ax, 5.5, 8.0, 7.2, y_feature + 0.45)

# Arrows from features to distance calculation
create_arrow(ax, 2.5, y_feature - 0.45, 4.2, 6.3)
create_arrow(ax, 7.5, y_feature - 0.45, 5.8, 6.3)

# 4. Distance Calculation
create_box(ax, 5, 5.9, 3.0, 0.7, 
          '3. Frame-to-Frame Distance\n(Chi-square + L2)', color_analysis)
create_arrow(ax, 5, 5.55, 5, 5.1)

# 5. Smoothing
create_box(ax, 5, 4.7, 2.5, 0.7, 
          '4. Smooth Distance Curve\n(Moving Average)', color_analysis)
create_arrow(ax, 5, 4.35, 5, 3.9)

# 6. Boundary Detection
create_box(ax, 5, 3.5, 2.8, 0.7, 
          '5. Detect Shot Boundaries\n(Adaptive Threshold)', color_analysis)
create_arrow(ax, 5, 3.15, 5, 2.7)

# 7. Keyframe Extraction
create_box(ax, 5, 2.3, 2.5, 0.7, 
          '6. Extract Keyframes\n(1 per shot)', color_process)
create_arrow(ax, 5, 1.95, 5, 1.5)

# 8. Export (parallel outputs)
y_output = 0.8
create_box(ax, 1.5, y_output, 1.6, 0.7, 
          'Storyboard\n.png', color_output, 10)
create_box(ax, 3.5, y_output, 1.6, 0.7, 
          'Boundaries\n.json', color_output, 10)
create_box(ax, 5.5, y_output, 1.6, 0.7, 
          'Distance Plot\n.png', color_output, 10)
create_box(ax, 7.5, y_output, 1.6, 0.7, 
          'Summary Video\n.mp4', color_output, 10)

# Arrows to outputs
create_arrow(ax, 4.2, 1.5, 1.8, y_output + 0.35)
create_arrow(ax, 4.6, 1.5, 3.5, y_output + 0.35)
create_arrow(ax, 5.4, 1.5, 5.5, y_output + 0.35)
create_arrow(ax, 5.8, 1.5, 7.2, y_output + 0.35)

# Add legend
legend_elements = [
    mpatches.Patch(facecolor=color_input, edgecolor='black', label='Input'),
    mpatches.Patch(facecolor=color_process, edgecolor='black', label='Processing'),
    mpatches.Patch(facecolor=color_feature, edgecolor='black', label='Feature Extraction'),
    mpatches.Patch(facecolor=color_analysis, edgecolor='black', label='Analysis'),
    mpatches.Patch(facecolor=color_output, edgecolor='black', label='Output')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10, 
         framealpha=0.9, bbox_to_anchor=(0, 1))

# Add info box
info_text = """Key Features:
• Color-based: HSV histograms
• Structure-based: Edge histograms
• Adaptive thresholding
• Temporal smoothing
• Multiple output formats"""

ax.text(9.5, 11.2, info_text, fontsize=9, 
       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
       verticalalignment='top', horizontalalignment='right',
       family='monospace')

plt.tight_layout()
plt.savefig('/home/runner/work/automatic-video-summarization/automatic-video-summarization/docs/pipeline.png', 
           dpi=300, bbox_inches='tight', facecolor='white')
print("Pipeline diagram saved to: docs/pipeline.png")

# Also create a simplified version
fig2, ax2 = plt.subplots(figsize=(10, 8))
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis('off')

ax2.text(5, 9.5, 'Video Summarization Pipeline (Simplified)', 
        fontsize=16, fontweight='bold', ha='center')

steps = [
    (8.5, 'INPUT:\nVideo File'),
    (7.5, 'STEP 1:\nLoad & Sample Frames'),
    (6.5, 'STEP 2:\nExtract Features\n(Color + Edges)'),
    (5.5, 'STEP 3:\nCompute Distances'),
    (4.5, 'STEP 4:\nSmooth & Threshold'),
    (3.5, 'STEP 5:\nDetect Boundaries'),
    (2.5, 'STEP 6:\nExtract Keyframes'),
    (1.5, 'OUTPUT:\nStoryboard, JSON,\nPlots, Video'),
]

for i, (y, text) in enumerate(steps):
    if i == 0:
        color = color_input
    elif i == len(steps) - 1:
        color = color_output
    else:
        color = color_process
    
    create_box(ax2, 5, y, 3.5, 0.7, text, color, 11)
    if i < len(steps) - 1:
        create_arrow(ax2, 5, y - 0.35, 5, steps[i+1][0] + 0.35)

plt.tight_layout()
plt.savefig('/home/runner/work/automatic-video-summarization/automatic-video-summarization/docs/pipeline_simple.png', 
           dpi=200, bbox_inches='tight', facecolor='white')
print("Simplified pipeline diagram saved to: docs/pipeline_simple.png")

plt.close('all')
