# Backend

The application encompasses a central API service and five auxiliary modules, including a database, worker daemons, 
a messaging queue, a frontend, and a DICOM service. The API, developed using the asynchronous Python framework 
[FastAPI](https://fastapi.tiangolo.com/), is the main component of the application. It controls all communication between the five auxiliary 
components, shown in the following architecture diagram.

![Alt](assets/architecture.png)

The DICOM service, implemented using the Python package pynetdicom, governs both the input and output
of DICOM images. RAIVEN conforms to all DICOM networking standards; it can be integrated seamlessly with all 
DICOM enabled software and equipment present in nuclear medicine and radiology departments. 

The RAIVEN allows users to build processing pipelines using a visual interface by connecting different algorithms developed by 
researchers. These algorithms are added to RAIVEN as Docker containers. With Docker as the underlying mechanism 
for our application, tools are easy to update, language agnostic, and maintained in separate virtual environments.

## Models

The models define the entity-relationship model in the database, and can be found under `\backend\api\models`.

## Schemas

The definitions of how data is to be sent and received by the internal API. They can be found under `\backend\api\schemas`.

## Routes

The internal API routes that can be used by the frontend, and pull information from the database. 
They can be found under `\backend\api\routes`. Middleware for the routes can be found under `\backend\api\middleware`.

## Pipelining Logic

All the pipelining logic can be found the folder `\backend\api\pipelining`. At its core, the pipeline module constructs a
directed graph to determine when to run pipeline nodes.
