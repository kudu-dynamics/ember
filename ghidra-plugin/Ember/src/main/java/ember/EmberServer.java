
package ember;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import java.util.logging.Logger;

/**
 * Server that manages startup/shutdown of a {@code Greeter} server.
 */
public class EmberServer {
  private static final Logger logger = Logger.getLogger(EmberServer.class.getName());

  private Server server;

    private static EmberPlugin plugin;
    
    public EmberServer(EmberPlugin plugin) {
        this.plugin = plugin;
    }
    
    public void start() throws IOException {
    /* The port on which the server should run */
    int port = 50058;
    server = ServerBuilder.forPort(port)
        .addService(new LocationSyncImpl())
        .build()
        .start();
    plugin.logInfo("Ember Location Server started on port: " + port);
    Runtime.getRuntime().addShutdownHook(new Thread() {
      @Override
      public void run() {
        // Use stderr here since the logger may have been reset by its JVM shutdown hook.
        System.err.println("*** shutting down gRPC server since JVM is shutting down");
        try {
          EmberServer.this.stop();
        } catch (InterruptedException e) {
          e.printStackTrace(System.err);
        }
        System.err.println("*** server shut down");
      }
    });
  }

  private void stop() throws InterruptedException {
    if (server != null) {
      server.shutdown().awaitTermination(30, TimeUnit.SECONDS);
    }
  }

  /**
   * Await termination on the main thread since the grpc library uses daemon threads.
   */
  public void blockUntilShutdown() throws InterruptedException {
    if (server != null) {
      server.awaitTermination();
    }
  }

  // /**
  //  * Main launches the server from the command line.
  //  */
  // public static void main(String[] args) throws IOException, InterruptedException {
  //   final EmberServer server = new EmberServer();
  //   server.start();
  //   server.blockUntilShutdown();
  // }

  static class LocationSyncImpl extends LocationSyncGrpc.LocationSyncImplBase {

    @Override
    public void setLocation(Location req, StreamObserver<SetLocationReply> responseObserver) {
        SetLocationReply reply = SetLocationReply.newBuilder().setMessage("Setting address to: " + String.valueOf(req.getOffset())).build();
        plugin.changeToOffset(req.getOffset());
        responseObserver.onNext(reply);
        responseObserver.onCompleted();
    }
  }
}
