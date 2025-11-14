```mermaid
graph TD
    SP[Scan Processor] --> RS[Risk Scorer]
    RS --> CM[Case Manager]
    CM --> WT[WorldTracer Handler]
    CM --> CD[Courier Dispatch]
    CM --> PC[Passenger Comms]
    DF[Data Fusion] --> SE[Semantic Enrichment]
    SE --> RS
    SP -.->|scan events| DF
    WT -.->|PIR data| DF
```
