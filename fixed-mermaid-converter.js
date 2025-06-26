// Mermaid to Google Drawing Objects Generator
// Creates actual shapes, lines, arrows, and text boxes with proper positioning and sizing

// ============================================================================
// MAIN FUNCTION - INSERT YOUR MERMAID CODE HERE
// Fixed: Notes now properly increment messageIndex for correct ordering
// ============================================================================
function createMySequenceDiagram() {
  // REPLACE THE MERMAID CODE BELOW WITH YOUR ACTUAL SEQUENCE DIAGRAM
  const myMermaidCode = `
sequenceDiagram
    participant A as Alice
    participant B as Bob
    participant C as Charlie
    
    Note over A, C: Process begins
    A->>B: Hello Bob!
    B->>C: Bob tells Charlie
    
    alt Success
        C-->>B: Got it
        B-->>A: Charlie says hi
    else Failure
        C-->>B: Error occurred
        B-->>A: Something went wrong
    end
    
    opt Log the interaction
        B->>B: Log to database
    end
    
    rect rgb(230, 255, 230)
        Note over A, C: Cleanup phase
        A->>C: Direct cleanup
        C-->>A: Cleanup complete
    end
    
    Note over A, C: Process complete
  `;
  
  return createDrawingObjects(myMermaidCode);
}

// ============================================================================
// CORE FUNCTIONS - DO NOT MODIFY
// ============================================================================

// Main function - creates actual drawing objects from mermaid code
function createDrawingObjects(mermaidCode) {
  console.log("Parsing mermaid diagram...");
  
  const diagram = parseMermaid(mermaidCode);
  
  if (diagram.participants.length === 0) {
    console.log("❌ No participants found");
    return null;
  }
  
  console.log(`✅ Parsed: ${diagram.participants.length} participants, ${diagram.messages.length} messages`);
  
  // Create actual drawing objects
  return generateDrawingObjects(diagram);
}

// Parse mermaid sequence diagram with alt/opt blocks, rect blocks, and notes
function parseMermaid(mermaidCode) {
  const lines = mermaidCode.split('\n').filter(line => line.trim());
  const participants = [];
  const messages = [];
  const blocks = []; // For alt/opt/rect blocks
  const notes = []; // For spanning notes
  
  let currentBlocks = []; // Stack for nested blocks
  let messageIndex = 0;
  
  lines.forEach((line, lineIndex) => {
    line = line.trim();
    
    // Parse participants
    const participantMatch = line.match(/participant\s+(\w+)(?:\s+as\s+(.+))?/);
    if (participantMatch) {
      participants.push({
        id: participantMatch[1],
        name: participantMatch[2] || participantMatch[1]
      });
      return;
    }
    
    // Parse rect blocks with custom colors
    const rectMatch = line.match(/^rect\s+rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
    if (rectMatch) {
      const [, r, g, b] = rectMatch;
      
      // Convert RGB to hex
      const toHex = (value) => {
        const hex = parseInt(value).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      };
      
      const hexColor = `#${toHex(r)}${toHex(g)}${toHex(b)}`;
      
      // For rect blocks, use the original color as background (don't make it lighter)
      // Create darker version for border (subtract 60 from each component, min 0)
      const darkR = Math.max(0, parseInt(r) - 60);
      const darkG = Math.max(0, parseInt(g) - 60);
      const darkB = Math.max(0, parseInt(b) - 60);
      const darkHexColor = `#${toHex(darkR)}${toHex(darkG)}${toHex(darkB)}`;
      
      const block = {
        type: 'rect',
        color: hexColor,
        backgroundColor: hexColor, // Use original color, not lighter
        borderColor: darkHexColor, // Darker shade for border
        startMessage: messageIndex,
        endMessage: null,
        condition: `Custom Section` // Default label
      };
      currentBlocks.push(block);
      blocks.push(block);
      return;
    }
    
    // Parse alt/opt blocks
    const altMatch = line.match(/^(alt|opt)\s+(.+)/);
    if (altMatch) {
      const block = {
        type: altMatch[1],
        condition: altMatch[2],
        startMessage: messageIndex,
        endMessage: null,
        sections: [{ condition: altMatch[2], startMessage: messageIndex, endMessage: null }]
      };
      currentBlocks.push(block);
      blocks.push(block);
      return;
    }
    
    // Parse notes (case-insensitive, more flexible patterns)
    const noteMatch = line.match(/^(note|Note)\s+(over|left of|right of)\s+([^:]+):\s*(.+)/i);
    if (noteMatch) {
      const [, , position, participantsList, text] = noteMatch;
      const participantIds = participantsList.split(',').map(p => p.trim());
      
      notes.push({
        type: 'note',
        position: position,
        participants: participantIds,
        text: text,
        messageIndex: messageIndex
      });
      
      console.log(`Found note: "${text}" over [${participantIds.join(', ')}]`);
      messageIndex++; // INCREMENT for notes too!
      return;
    }
    
    // Parse spanning notes with case-insensitive matching
    const spanningNoteMatch = line.match(/^(note|Note)\s+over\s+([^:]+):\s*(.+)/i);
    if (spanningNoteMatch) {
      const [, , participantsList, text] = spanningNoteMatch;
      const participantIds = participantsList.split(',').map(p => p.trim());
      
      notes.push({
        type: 'spanning_note',
        position: 'over',
        participants: participantIds,
        text: text,
        messageIndex: messageIndex
      });
      
      console.log(`Found spanning note: "${text}" over [${participantIds.join(', ')}]`);
      messageIndex++; // INCREMENT for spanning notes too!
      return;
    }
    
    // Debug: log any line that starts with "note" (case-insensitive) but doesn't match
    if (line.toLowerCase().startsWith('note')) {
      console.log(`Note line not matched: "${line}"`);
    }
    
    // Parse else
    if (line === 'else' || line.match(/^else\s+(.+)/)) {
      if (currentBlocks.length > 0) {
        const currentBlock = currentBlocks[currentBlocks.length - 1];
        if (currentBlock.type !== 'rect') { // Rect blocks don't have else
          // End current section
          if (currentBlock.sections && currentBlock.sections.length > 0) {
            currentBlock.sections[currentBlock.sections.length - 1].endMessage = messageIndex - 1;
          }
          // Start new section
          const condition = line.match(/^else\s+(.+)/) ? line.match(/^else\s+(.+)/)[1] : 'else';
          currentBlock.sections.push({ condition, startMessage: messageIndex, endMessage: null });
        }
      }
      return;
    }
    
    // Parse end
    if (line === 'end') {
      if (currentBlocks.length > 0) {
        const block = currentBlocks.pop();
        block.endMessage = messageIndex - 1;
        // End the last section for alt/opt blocks
        if (block.sections && block.sections.length > 0) {
          block.sections[block.sections.length - 1].endMessage = messageIndex - 1;
        }
      }
      return;
    }
    
    // Parse messages
    const messageMatch = line.match(/(\w+)(--?>>?)(\w+):\s*(.+)/);
    if (messageMatch) {
      const [, from, arrow, to, text] = messageMatch;
      
      // Auto-add participants if not declared
      if (!participants.find(p => p.id === from)) {
        participants.push({ id: from, name: from });
      }
      if (!participants.find(p => p.id === to)) {
        participants.push({ id: to, name: to });
      }
      
      messages.push({
        from,
        to,
        text,
        async: arrow.includes('--'),
        messageIndex: messageIndex,
        blockContext: [...currentBlocks] // Capture current block context
      });
      
      messageIndex++;
    }
  });
  
  // Close any remaining open blocks
  currentBlocks.forEach(block => {
    block.endMessage = messageIndex - 1;
    if (block.sections && block.sections.length > 0) {
      block.sections[block.sections.length - 1].endMessage = messageIndex - 1;
    }
  });
  
  console.log(`Parsed: ${participants.length} participants, ${messages.length} messages, ${blocks.length} blocks, ${notes.length} notes`);
  blocks.forEach((block, i) => {
    if (block.type === 'rect') {
      console.log(`Block ${i + 1}: ${block.type} with color ${block.color}`);
    } else {
      console.log(`Block ${i + 1}: ${block.type} with ${block.sections ? block.sections.length : 0} sections`);
    }
  });
  notes.forEach((note, i) => {
    console.log(`Note ${i + 1}: ${note.type} over [${note.participants.join(', ')}]: "${note.text}"`);
  });
  
  return { participants, messages, blocks, notes };
}

// Generate actual drawing objects (shapes, lines, arrows, text) with alt/opt support
function generateDrawingObjects(diagram) {
  try {
    // Create Google Slides presentation (supports all drawing primitives)
    const presentation = SlidesApp.create(`Sequence Diagram Objects ${new Date().toISOString().slice(0,16)}`);
    const slide = presentation.getSlides()[0];
    
    console.log("Creating drawing objects with alt/opt support...");
    
    // Configuration - adjusted for better sizing
    const config = {
      participantWidth: 160, // Increased for longer text
      participantHeight: 50,
      participantSpacing: 220, // Increased spacing
      messageSpacing: 70,
      noteSpacing: 50, // Additional space for notes
      startX: 80,
      startY: 60,
      blockPadding: 15,
      messageTextWidth: 180, // Increased for longer messages
      messageTextHeight: 40  // Increased for multi-line text
    };
    
    if (!diagram.notes) diagram.notes = []; // Ensure notes array exists
    if (!diagram.blocks) diagram.blocks = []; // Ensure blocks array exists
    
    const { participants, messages, blocks, notes } = diagram;
    
    // Create a map to track Y positions for each element (messages and notes)
    const elementPositions = [];
    let currentY = config.startY + config.participantHeight + 30;
    
    // Build a combined list of messages and notes sorted by messageIndex
    const allElements = [];
    messages.forEach((msg, idx) => {
      allElements.push({ type: 'message', data: msg, index: msg.messageIndex, originalOrder: idx });
    });
    notes.forEach((note, idx) => {
      allElements.push({ type: 'note', data: note, index: note.messageIndex, originalOrder: idx + 1000 }); // Offset to distinguish from messages
    });
    
    // Sort by message index (primary) and original order (secondary for stability)
    allElements.sort((a, b) => {
      if (a.index !== b.index) return a.index - b.index;
      return a.originalOrder - b.originalOrder;
    });
    
    // Calculate Y positions for each element
    allElements.forEach((element, idx) => {
      elementPositions[element.index] = elementPositions[element.index] || {};
      elementPositions[element.index][element.type] = currentY;
      
      if (element.type === 'note') {
        currentY += config.noteSpacing;
      } else {
        // Check if there's a note after this message
        const hasNoteAfter = idx + 1 < allElements.length && 
                           allElements[idx + 1].type === 'note' && 
                           allElements[idx + 1].index === element.index;
        currentY += hasNoteAfter ? config.messageSpacing : config.messageSpacing;
      }
    });
    
    // Calculate total height needed
    const totalHeight = currentY + config.participantHeight + 60;
    const totalWidth = config.startX * 2 + (participants.length * config.participantSpacing);
    
    console.log(`Canvas size: ${totalWidth} x ${totalHeight}`);
    console.log(`Will create ${blocks.length} blocks and ${notes.length} notes`);
    
    // Create alt/opt/rect block backgrounds FIRST (so they appear behind other elements)
    console.log(`Creating ${blocks.length} background blocks...`);
    blocks.forEach((block, blockIndex) => {
      console.log(`Processing block ${blockIndex + 1}: ${block.type}`);
      
      // Find the first and last elements in this block
      let blockStartY = Number.MAX_VALUE;
      let blockEndY = 0;
      
      // Check all elements to find those within this block's message range
      allElements.forEach(element => {
        if (element.index >= block.startMessage && element.index <= block.endMessage) {
          const pos = elementPositions[element.index][element.type];
          if (pos < blockStartY) blockStartY = pos;
          if (pos > blockEndY) blockEndY = pos;
        }
      });
      
      // Special handling: If the first element in the block is a note, ensure block starts above it
      const firstElementInBlock = allElements.find(el => 
        el.index >= block.startMessage && el.index <= block.endMessage
      );
      if (firstElementInBlock && firstElementInBlock.type === 'note') {
        blockStartY -= 35; // Extra space above notes at block start
      } else {
        blockStartY -= 20; // Standard space above other elements
      }
      
      blockEndY += config.messageSpacing - 20; // End below the last element
      const blockHeight = blockEndY - blockStartY + config.blockPadding * 2;
      
      // Determine which participants are involved in this block
      const blockMessages = messages.filter(msg => 
        msg.messageIndex >= block.startMessage && msg.messageIndex <= block.endMessage
      );
      const involvedParticipants = new Set();
      blockMessages.forEach(msg => {
        involvedParticipants.add(msg.from);
        involvedParticipants.add(msg.to);
      });
      
      if (involvedParticipants.size > 0) {
        const participantIndices = Array.from(involvedParticipants).map(id => 
          participants.findIndex(p => p.id === id)
        ).filter(index => index !== -1);
        
        const minIndex = Math.min(...participantIndices);
        const maxIndex = Math.max(...participantIndices);
        
        const blockStartX = config.startX + (minIndex * config.participantSpacing) - config.blockPadding;
        const blockWidth = (maxIndex - minIndex + 1) * config.participantSpacing + config.blockPadding * 2;
        
        // Determine background and border colors based on block type
        let bgColor, borderColor;
        
        if (block.type === 'rect') {
          // Custom rect block with user-specified colors
          bgColor = block.backgroundColor;
          borderColor = block.borderColor;
        } else if (block.type === 'alt') {
          bgColor = '#fff8e1'; // Yellow for alt
          borderColor = '#ff9800';
        } else if (block.type === 'opt') {
          bgColor = '#f3e5f5'; // Purple for opt
          borderColor = '#9c27b0';
        }
        
        // Create background rectangle
        const background = slide.insertShape(
          SlidesApp.ShapeType.RECTANGLE,
          blockStartX, blockStartY - config.blockPadding,
          blockWidth, blockHeight
        );
        
        background.getFill().setSolidFill(bgColor);
        background.getBorder().getLineFill().setSolidFill(borderColor);
        background.getBorder().setWeight(block.type === 'rect' ? 2 : 1);
        background.getBorder().setDashStyle(block.type === 'rect' ? SlidesApp.DashStyle.SOLID : SlidesApp.DashStyle.DASH);
        
        // Add block label (only for alt/opt, rect blocks usually don't have labels)
        if (block.type !== 'rect') {
          const labelText = `${block.type}: ${block.condition}`;
          const label = slide.insertTextBox(
            labelText,
            blockStartX + 5, blockStartY - config.blockPadding + 2,
            blockWidth - 10, 20
          );
          
          label.getText().getTextStyle()
            .setFontSize(9)
            .setBold(true)
            .setForegroundColor(borderColor);
          label.getFill().setTransparent();
          label.getBorder().setTransparent();
          
          // Add section dividers for alt blocks with else
          if (block.type === 'alt' && block.sections && block.sections.length > 1) {
            block.sections.forEach((section, sectionIndex) => {
              if (sectionIndex > 0) {
                // Find the Y position for the divider
                let dividerY = Number.MAX_VALUE;
                allElements.forEach(element => {
                  if (element.index === section.startMessage) {
                    const pos = elementPositions[element.index][element.type];
                    if (pos < dividerY) dividerY = pos;
                  }
                });
                dividerY -= 15; // Position slightly above the first message of the section
                
                const divider = slide.insertLine(
                  SlidesApp.LineCategory.STRAIGHT,
                  blockStartX, dividerY,
                  blockStartX + blockWidth, dividerY
                );
                
                divider.getLineFill().setSolidFill(borderColor);
                divider.setWeight(1);
                divider.setDashStyle(SlidesApp.DashStyle.DOT);
                
                // Add else label
                if (section.condition !== block.condition) {
                  const elseLabel = slide.insertTextBox(
                    section.condition,
                    blockStartX + 5, dividerY - 10,
                    100, 15
                  );
                  elseLabel.getText().getTextStyle()
                    .setFontSize(8)
                    .setItalic(true)
                    .setForegroundColor(borderColor);
                  elseLabel.getFill().setTransparent();
                  elseLabel.getBorder().setTransparent();
                }
              }
            });
          }
        }
        
        console.log(`Created ${block.type} block background with color ${bgColor}`);
      }
    });
    
    // Create spanning notes - Now with their own row
    console.log(`Creating ${notes.length} spanning notes...`);
    notes.forEach((note, noteIndex) => {
      console.log(`Processing note ${noteIndex + 1}: "${note.text}"`);
      
      // Get the Y position for this note from our calculated positions
      const noteY = elementPositions[note.messageIndex]?.note;
      if (!noteY) {
        console.log(`Warning: No position found for note at index ${note.messageIndex}`);
        return;
      }
      
      // Find the participant indices for spanning
      const noteParticipantIndices = note.participants.map(id => 
        participants.findIndex(p => p.id === id)
      ).filter(index => index !== -1);
      
      if (noteParticipantIndices.length > 0) {
        const minIndex = Math.min(...noteParticipantIndices);
        const maxIndex = Math.max(...noteParticipantIndices);
        
        const noteStartX = config.startX + (minIndex * config.participantSpacing);
        const noteWidth = (maxIndex - minIndex + 1) * config.participantSpacing;
        const noteHeight = 35; // Height for note box
        
        // Create note background
        const noteBox = slide.insertShape(
          SlidesApp.ShapeType.RECTANGLE,
          noteStartX, noteY,
          noteWidth, noteHeight
        );
        
        noteBox.getFill().setSolidFill('#fffde7'); // Light yellow for notes
        noteBox.getBorder().getLineFill().setSolidFill('#f57f17');
        noteBox.getBorder().setWeight(1);
        
        // Add note text
        noteBox.getText().setText(note.text);
        noteBox.getText().getTextStyle()
          .setFontSize(10)
          .setItalic(true)
          .setForegroundColor('#333333');
        noteBox.getText().getParagraphStyle()
          .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
        
        console.log(`Created spanning note: "${note.text}" at Y=${noteY}`);
      }
    });
    
    // Create participant boxes (rectangles with text) - TOP
    participants.forEach((participant, index) => {
      const x = config.startX + (index * config.participantSpacing);
      const y = config.startY;
      
      // FIX 2: Calculate text width dynamically
      const tempTextBox = slide.insertTextBox(participant.name, 0, 0, 1000, 50);
      tempTextBox.getText().getTextStyle()
        .setFontSize(12)
        .setBold(true);
      const textWidth = Math.max(config.participantWidth, participant.name.length * 10 + 20);
      tempTextBox.remove();
      
      // Create rectangle shape with dynamic width
      const rect = slide.insertShape(
        SlidesApp.ShapeType.RECTANGLE,
        x - (textWidth - config.participantWidth) / 2, y, textWidth, config.participantHeight
      );
      
      // Style the rectangle
      rect.getFill().setSolidFill('#e3f2fd');
      rect.getBorder().getLineFill().setSolidFill('#1976d2');
      rect.getBorder().setWeight(2);
      
      // Set text
      rect.getText().setText(participant.name);
      rect.getText().getTextStyle()
        .setFontSize(12)
        .setBold(true)
        .setForegroundColor('#1976d2');
      rect.getText().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
      
      console.log(`Created participant box: ${participant.name}`);
      
      // Create lifeline (vertical dashed line)
      const lifelineX = x + config.participantWidth / 2;
      const lifelineStart = y + config.participantHeight;
      const lifelineEnd = totalHeight - config.participantHeight - 60;
      
      const lifeline = slide.insertLine(
        SlidesApp.LineCategory.STRAIGHT,
        lifelineX, lifelineStart,
        lifelineX, lifelineEnd
      );
      
      lifeline.getLineFill().setSolidFill('#9e9e9e');
      lifeline.setWeight(2);
      lifeline.setDashStyle(SlidesApp.DashStyle.DASH);
      
      console.log(`Created lifeline for: ${participant.name}`);
      
      // Create participant box at BOTTOM with dynamic width
      const bottomY = lifelineEnd;
      const bottomRect = slide.insertShape(
        SlidesApp.ShapeType.RECTANGLE,
        x - (textWidth - config.participantWidth) / 2, bottomY, textWidth, config.participantHeight
      );
      
      bottomRect.getFill().setSolidFill('#e3f2fd');
      bottomRect.getBorder().getLineFill().setSolidFill('#1976d2');
      bottomRect.getBorder().setWeight(2);
      
      bottomRect.getText().setText(participant.name);
      bottomRect.getText().getTextStyle()
        .setFontSize(12)
        .setBold(true)
        .setForegroundColor('#1976d2');
      bottomRect.getText().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
      
      console.log(`Created bottom participant box: ${participant.name}`);
    });
    
    // Create message arrows and labels
    messages.forEach((message, index) => {
      const fromIndex = participants.findIndex(p => p.id === message.from);
      const toIndex = participants.findIndex(p => p.id === message.to);
      
      if (fromIndex === -1 || toIndex === -1) {
        console.log(`Warning: Participant not found for message: ${message.from} -> ${message.to}`);
        return;
      }
      
      const fromX = config.startX + (fromIndex * config.participantSpacing) + (config.participantWidth / 2);
      const toX = config.startX + (toIndex * config.participantSpacing) + (config.participantWidth / 2);
      
      // Get Y position from our calculated positions
      const y = elementPositions[message.messageIndex]?.message;
      if (!y) {
        console.log(`Warning: No position found for message at index ${message.messageIndex}`);
        return;
      }
      
      console.log(`Creating message ${index + 1}: ${message.from} -> ${message.to} at Y=${y}`);
      
      if (fromX === toX) {
        // Self-message: create loop
        const loopWidth = 60;
        
        // Horizontal line out
        const lineOut = slide.insertLine(
          SlidesApp.LineCategory.STRAIGHT,
          fromX, y,
          fromX + loopWidth, y
        );
        styleMessageLine(lineOut, message.async);
        
        // Vertical line down
        const lineDown = slide.insertLine(
          SlidesApp.LineCategory.STRAIGHT,
          fromX + loopWidth, y,
          fromX + loopWidth, y + 30
        );
        styleMessageLine(lineDown, message.async);
        
        // Horizontal line back with arrow pointing TO the entity
        const lineBack = slide.insertLine(
          SlidesApp.LineCategory.STRAIGHT,
          fromX + loopWidth, y + 30,
          fromX, y + 30
        );
        styleMessageLine(lineBack, message.async);
        lineBack.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW); // Arrow points TO the entity
        
        // Text box for self-message
        const textBox = slide.insertTextBox(
          message.text,
          fromX + loopWidth + 10, y - 10,
          config.messageTextWidth, config.messageTextHeight
        );
        styleMessageText(textBox);
        
      } else {
        // Regular message arrow
        const arrow = slide.insertLine(
          SlidesApp.LineCategory.STRAIGHT,
          fromX, y,
          toX, y
        );
        
        styleMessageLine(arrow, message.async);
        
        // FIX 3: Correct arrow direction for return messages
        // For async (dashed) messages, the convention is that the arrow points FROM the sender TO the receiver
        // regardless of left/right position
        if (message.async) {
          // Async messages (returns) - arrow always points to the receiver
          arrow.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
        } else {
          // Sync messages - arrow points in the direction of the message
          if (fromX < toX) {
            arrow.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
          } else {
            arrow.setStartArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
          }
        }
        
        // Text box for message label - positioned above the line
        const textX = Math.min(fromX, toX) + Math.abs(fromX - toX) / 2 - config.messageTextWidth / 2;
        const textY = y - 25; // Slightly more spacing above line
        
        const textBox = slide.insertTextBox(
          message.text,
          textX, textY,
          config.messageTextWidth, config.messageTextHeight
        );
        styleMessageText(textBox);
      }
    });
    
    // Add title text box
    const titleBox = slide.insertTextBox(
      'Sequence Diagram',
      config.startX, 10,
      totalWidth - config.startX * 2, 30
    );
    titleBox.getText().getTextStyle()
      .setFontSize(16)
      .setBold(true)
      .setForegroundColor('#1976d2');
    titleBox.getText().getParagraphStyle()
      .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
    titleBox.getFill().setTransparent();
    titleBox.getBorder().setTransparent();
    
    const url = presentation.getUrl();
    console.log(`✅ Drawing objects created: ${url}`);
    console.log(`📋 Features: Alt/Opt blocks, custom rect blocks, spanning notes, bottom entities`);
    console.log(`📋 Fixed issues: Note positioning, text box sizing, arrow directions`);
    console.log(`📋 Notes now have their own dedicated rows and proper sequence ordering`);
    console.log(`📋 To copy to Google Docs:`);
    console.log(`   1. Open the presentation above`);
    console.log(`   2. Select all objects (Ctrl+A)`);
    console.log(`   3. Copy (Ctrl+C)`);
    console.log(`   4. Paste into your Google Doc (Ctrl+V)`);
    console.log(`   Result: Native drawing objects in your document!`);
    
    return url;
    
  } catch (error) {
    console.error("Error creating drawing objects:", error);
    return null;
  }
}

// Style message lines (solid for sync, dashed for async)
function styleMessageLine(line, isAsync) {
  line.getLineFill().setSolidFill(isAsync ? '#666666' : '#333333');
  line.setWeight(2);
  if (isAsync) {
    line.setDashStyle(SlidesApp.DashStyle.DASH);
  }
}

// Style message text boxes
function styleMessageText(textBox) {
  textBox.getText().getTextStyle()
    .setFontSize(10)
    .setBold(false)
    .setForegroundColor('#333333');
  textBox.getText().getParagraphStyle()
    .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
  textBox.getFill().setSolidFill('#ffffff');
  textBox.getBorder().getLineFill().setSolidFill('#cccccc');
  textBox.getBorder().setWeight(1);
}

// ============================================================================
// UTILITY FUNCTIONS FOR CREATING COMPACT DIAGRAMS
// ============================================================================

// Generate compact version for large diagrams (fits standard canvas)
function generateCompactDiagram() {
  const myMermaidCode = `
sequenceDiagram
    participant U as User
    participant S as System
    participant D as Database
    participant A as API
    
    U->>S: Request
    S->>D: Query
    D-->>S: Data
    S->>A: Process
    A-->>S: Result
    S-->>U: Response
  `;
  
  return createCompactDrawingObjects(myMermaidCode);
}

// Create extra-compact drawing objects for large diagrams
function createCompactDrawingObjects(mermaidCode) {
  try {
    console.log("Parsing mermaid diagram...");
    
    if (!mermaidCode) {
      console.log("❌ No mermaid code provided");
      return null;
    }
    
    const diagram = parseMermaid(mermaidCode);
    
    if (diagram.participants.length === 0) {
      console.log("❌ No participants found");
      return null;
    }
    
    console.log(`✅ Parsed: ${diagram.participants.length} participants, ${diagram.messages.length} messages`);
    
    const presentation = SlidesApp.create(`Compact Sequence Diagram ${new Date().toISOString().slice(0,16)}`);
    const slide = presentation.getSlides()[0];
    
    // Extra compact configuration for large diagrams
    const config = {
      participantWidth: 80,
      participantHeight: 30,
      participantSpacing: 100,
      messageSpacing: 35,
      startX: 20,
      startY: 30,
      maxCanvasWidth: 720,   // Fits in standard Google Docs canvas
      maxCanvasHeight: 540
    };
    
    const { participants, messages, blocks } = diagram;
    
    console.log(`Creating compact diagram: ${participants.length} participants, ${messages.length} messages`);
    
    // Adjust spacing if too many participants
    if (participants.length > 6) {
      config.participantSpacing = Math.min(100, 650 / participants.length);
      config.participantWidth = Math.min(80, config.participantSpacing - 20);
    }
    
    // Create participant boxes
    participants.forEach((participant, index) => {
      const x = config.startX + (index * config.participantSpacing);
      const y = config.startY;
      
      const rect = slide.insertShape(
        SlidesApp.ShapeType.RECTANGLE,
        x, y, config.participantWidth, config.participantHeight
      );
      
      rect.getFill().setSolidFill('#e3f2fd');
      rect.getBorder().getLineFill().setSolidFill('#1976d2');
      rect.getBorder().setWeight(1);
      
      // Compact text
      rect.getText().setText(participant.name);
      rect.getText().getTextStyle()
        .setFontSize(9)
        .setBold(true)
        .setForegroundColor('#1976d2');
      rect.getText().getParagraphStyle()
        .setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
      
      // Shorter lifeline
      const lifelineX = x + config.participantWidth / 2;
      const lifelineStart = y + config.participantHeight;
      const lifelineEnd = config.startY + config.participantHeight + (messages.length * config.messageSpacing) + 20;
      
      const lifeline = slide.insertLine(
        SlidesApp.LineCategory.STRAIGHT,
        lifelineX, lifelineStart,
        lifelineX, lifelineEnd
      );
      
      lifeline.getLineFill().setSolidFill('#9e9e9e');
      lifeline.setWeight(1);
      lifeline.setDashStyle(SlidesApp.DashStyle.DASH);
    });
    
    // Create compact message arrows
    messages.forEach((message, index) => {
      const fromIndex = participants.findIndex(p => p.id === message.from);
      const toIndex = participants.findIndex(p => p.id === message.to);
      
      if (fromIndex === -1 || toIndex === -1) return;
      
      const fromX = config.startX + (fromIndex * config.participantSpacing) + (config.participantWidth / 2);
      const toX = config.startX + (toIndex * config.participantSpacing) + (config.participantWidth / 2);
      const y = config.startY + config.participantHeight + 20 + (index * config.messageSpacing);
      
      if (fromX === toX) {
        // Compact self-message
        const loopWidth = 30;
        
        const lineOut = slide.insertLine(SlidesApp.LineCategory.STRAIGHT, fromX, y, fromX + loopWidth, y);
        const lineDown = slide.insertLine(SlidesApp.LineCategory.STRAIGHT, fromX + loopWidth, y, fromX + loopWidth, y + 15);
        const lineBack = slide.insertLine(SlidesApp.LineCategory.STRAIGHT, fromX + loopWidth, y + 15, fromX, y + 15);
        
        [lineOut, lineDown, lineBack].forEach(line => {
          line.getLineFill().setSolidFill(message.async ? '#666666' : '#333333');
          line.setWeight(1);
          if (message.async) line.setDashStyle(SlidesApp.DashStyle.DASH);
        });
        
        lineBack.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW); // Arrow points TO the entity
        
        // Compact text
        const textBox = slide.insertTextBox(message.text, fromX + loopWidth + 5, y - 8, 80, 18);
        textBox.getText().getTextStyle().setFontSize(8);
        textBox.getText().getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
        textBox.getFill().setSolidFill('#ffffff');
        textBox.getBorder().getLineFill().setSolidFill('#cccccc');
        
      } else {
        // Regular compact arrow with fixed direction
        const arrow = slide.insertLine(SlidesApp.LineCategory.STRAIGHT, fromX, y, toX, y);
        
        arrow.getLineFill().setSolidFill(message.async ? '#666666' : '#333333');
        arrow.setWeight(1);
        if (message.async) arrow.setDashStyle(SlidesApp.DashStyle.DASH);
        
        // Fixed arrow direction logic
        if (message.async) {
          arrow.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
        } else {
          if (fromX < toX) {
            arrow.setEndArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
          } else {
            arrow.setStartArrow(SlidesApp.ArrowStyle.STEALTH_ARROW);
          }
        }
        
        // Compact message text
        const textX = Math.min(fromX, toX) + Math.abs(fromX - toX) / 2 - 30;
        const textY = y - 12;
        
        const textBox = slide.insertTextBox(message.text, textX, textY, 60, 15);
        textBox.getText().getTextStyle().setFontSize(8);
        textBox.getText().getParagraphStyle().setParagraphAlignment(SlidesApp.ParagraphAlignment.CENTER);
        textBox.getFill().setSolidFill('#ffffff');
        textBox.getBorder().getLineFill().setSolidFill('#cccccc');
      }
    });
    
    const url = presentation.getUrl();
    console.log(`✅ Compact drawing objects created: ${url}`);
    console.log(`📏 Optimized to fit standard Google Docs drawing canvas`);
    
    return url;
    
  } catch (error) {
    console.error("Error creating compact drawing objects:", error);
    return null;
  }
}

// ============================================================================
// TEST FUNCTIONS - Examples of various diagram features
// ============================================================================

// Test function with alt/opt blocks, rect blocks, and spanning notes
function testMermaidDiagram() {
  const testMermaid = `
sequenceDiagram
    participant A as User
    participant B as API
    participant C as Database
    A->>B: Login Request
    note over A, B: User authentication flow begins
    alt Valid Credentials
        B->>C: Query User
        C-->>B: User Data
        B-->>A: Login Success
    else Invalid Credentials
        B-->>A: Login Failed
    end
    opt Remember Me
        A->>B: Store Session
        B->>C: Save Session
        C-->>B: Session Saved
    end
    rect rgb(230, 255, 230)
        A->>B: Get Profile Request
        B->>C: Fetch User Profile
        C-->>B: Profile Data
        B-->>A: Profile Response
        note over B, C: Database optimization section
        B->>C: Update Last Access
        C-->>B: Updated
    end
    A->>B: Logout
    B-->>A: Logged Out
  `;
  
  return createDrawingObjects(testMermaid);
}

// Test function specifically for notes in their own rows
function testNotesInOwnRows() {
  const testMermaid = `
sequenceDiagram
    participant A as Alice
    participant B as Bob
    participant C as Charlie
    
    Note over A, C: System initialization
    A->>B: Hello Bob
    B-->>A: Hi Alice
    
    alt Authentication Check
        Note over A, B: Security verification required
        A->>B: Send credentials
        B->>C: Verify with system
        C-->>B: Verified
        B-->>A: Access granted
    else Authentication Failed
        B-->>A: Access denied
    end
    
    Note over B, C: Processing complete
    A->>C: Direct communication
    C-->>A: Response
  `;
  
  return createDrawingObjects(testMermaid);
}

// Test function with notes at beginning of blocks
function testNotesAtBlockStart() {
  const testMermaid = `
sequenceDiagram
    participant U as User
    participant S as System
    participant DB as Database
    
    U->>S: Initial request
    
    rect rgb(230, 255, 230)
        Note over U, DB: Data validation phase begins
        S->>DB: Query user data
        DB-->>S: User data returned
        S->>S: Validate data
        S-->>U: Validation complete
    end
    
    rect rgb(255, 230, 230)
        Note over S, DB: Error recovery section
        S->>DB: Retry failed operation
        DB-->>S: Operation successful
    end
    
    Note over U, DB: Process complete
    U->>S: Acknowledge completion
  `;
  
  return createDrawingObjects(testMermaid);
}

// Test function to verify note ordering fix
function testNoteOrderingFix() {
  const testMermaid = `
sequenceDiagram
    participant A as System A
    participant B as System B
    participant C as System C
    
    Note over A, C: Initial system state
    A->>B: First message
    Note over B, C: Mid-process checkpoint
    B->>C: Second message
    
    rect rgb(255, 230, 230)
        Note over A, C: Critical section begins
        A->>B: Critical operation 1
        B->>C: Critical operation 2
        Note over B, C: Validation point
        C-->>B: Response
        B-->>A: Confirmation
    end
    
    Note over A, C: All operations complete
  `;
  
  return createDrawingObjects(testMermaid);
}

// Test the exact Emergency Circuit Breaker scenario from the original diagram
function testEmergencyCircuitBreaker() {
  const testMermaid = `
sequenceDiagram
    participant U as User
    participant TA as Transfer Agent
    participant RA as RolesAuthority
    participant MMF as MMF Contract
    participant GM as Galaxy uMPC
    
    Note over U, GM: Emergency Circuit Breaker Scenario
    rect rgb(255, 230, 230)
        Note over TA, RA: Emergency Detected
        TA->>RA: pauseRole(specificRole)
        RA-->>TA: Role paused
        U->>MMF: Attempt operation
        MMF->>RA: doesUserHaveRole(user, role)
        RA-->>MMF: RequestedRolePaused error
        MMF-->>U: Transaction reverted - Role paused
        Note over GM, RA: Emergency Resolution
        GM->>RA: resumeRole(specificRole) [via Impenetrable Vault]
        RA-->>GM: Role resumed
    end
  `;
  
  return createDrawingObjects(testMermaid);
}