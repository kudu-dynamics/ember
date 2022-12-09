/* ###
 * IP: GHIDRA
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package ember;

import java.awt.BorderLayout;

import javax.swing.*;

import docking.ActionContext;
import docking.ComponentProvider;
import docking.action.DockingAction;
import docking.action.ToolBarData;
import ghidra.app.ExamplesPluginPackage;
import ghidra.app.plugin.PluginCategoryNames;
import ghidra.app.plugin.ProgramPlugin;
import ghidra.app.services.ConsoleService;
import ghidra.framework.plugintool.*;
import ghidra.framework.plugintool.util.PluginStatus;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.GenericAddress;
import ghidra.program.model.listing.Program;
import ghidra.program.util.ProgramSelection;
import ghidra.program.util.ProgramLocation;
import ghidra.util.HelpLocation;
import ghidra.util.Msg;
import resources.Icons;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import java.util.logging.Logger;
import java.lang.Thread;

/**
 * TODO: Provide class-level documentation that describes what this plugin does.
 */
//@formatter:off
@PluginInfo(
    status = PluginStatus.STABLE,
    packageName = ExamplesPluginPackage.NAME,
    category = PluginCategoryNames.EXAMPLES,
    shortDescription = "Interact with Ember.",
    description = "Basic interaction with Ember."
)
//@formatter:on
public class EmberPlugin extends ProgramPlugin {

    MyProvider provider;
    public static PluginTool main_tool;
    public static Program program;
    public static ConsoleService console;
    public static EmberPlugin plugin;
    Address lastActiveAddress;

    private static class EmberLocationServerThread extends Thread {
        public void run() {
            try {
                EmberServer server = new EmberServer(plugin);
                server.start();
                server.blockUntilShutdown();
            } catch (InterruptedException e) {
                e.printStackTrace(System.err);
            }
            catch (IOException e) {
                e.printStackTrace(System.err);
            }            
        }
    }

    
    /**
     * Plugin constructor.
     * 
     * @param tool The plugin tool that this plugin is added to.
     */
    public EmberPlugin(PluginTool tool) {
        super(tool, true, true);
   

        // TODO: Customize provider (or remove if a provider is not desired)
        String pluginName = getName();
        provider = new MyProvider(this, pluginName);

        // TODO: Customize help (or remove if help is not desired)
        String topicName = this.getClass().getPackage().getName();
        String anchorName = "HelpAnchor";
        provider.setHelpLocation(new HelpLocation(topicName, anchorName));
        plugin = this;
    }

    boolean unsafeGoTo(Address addr) {
        return this.goTo(addr);
    }

    public static void logInfo(String msg) {
        if (console != null) {
            console.println(msg);
        }
    }
    
    @Override
    public void init() {
        super.init();

        // TODO: Acquire services if necessary
    }

    @Override
    protected void programActivated(Program p) {
        super.programActivated(p);
        this.console = tool.getService(ConsoleService.class);
        this.console.println("program activated");
        program = p;

        EmberLocationServerThread serverThread = new EmberLocationServerThread();
        Thread thread = new Thread(serverThread);
        thread.start();
    }

    // Gets called whenever user clicks on new location
    @Override
    protected void locationChanged​(ProgramLocation loc) {
        super.locationChanged(loc);
        if (loc != null) {
            Address addr = loc.getAddress();
            if (addr != lastActiveAddress) {
                lastActiveAddress = addr;
                String offStr = String.format("0x%08x", addr.getOffset());
                if (console != null) { console.println("Offset: " + offStr); }
            }
        }
    }

    void changeToOffset(long offset) {
        if (program != null) {
            Address imgBase = program.getImageBase();
            Address addr = imgBase.getNewAddress(offset);
            String offStr = String.format("0x%08x", offset);

            if (unsafeGoTo(addr)) {
                lastActiveAddress = addr;
                logInfo("Going to address: " + offStr);
            }
            else {
                logInfo("Failed to go to address: " + offStr);
            }
        }
    }
    
    // Doesn't seem to get called.
    @Override
    protected void highlightChanged​(ProgramSelection hl) {
        super.highlightChanged(hl);
        if (console != null) { console.println("Highlight changed"); }
    }

    
    // TODO: If provider is desired, it is recommended to move it to its own file
    private static class MyProvider extends ComponentProvider {

      private JPanel panel;
      private DockingAction action;
      private EmberPlugin plugin;
      
      
      
        public MyProvider(EmberPlugin plugin, String owner) {
            super(plugin.getTool(), owner, owner);
      this.plugin = plugin;
            buildPanel();
            createActions();
        }

        // Customize GUI
        private void buildPanel() {
            panel = new JPanel(new BorderLayout());
            JTextArea textArea = new JTextArea(5, 25);
            textArea.setEditable(false);
            panel.add(new JScrollPane(textArea));
            setVisible(true);
        }

        // TODO: Customize actions
        private void createActions() {
            action = new DockingAction("My Action", getName()) {
                @Override
                public void actionPerformed(ActionContext context) {
                    Msg.showInfo(getClass(), panel, "Custom Action", "Whoa there!");
                    // try {
                    //     Thread.sleep(8000);
                    // } catch (InterruptedException e) {
                    //     e.printStackTrace(System.err);
                    // }

                    
                    // plugin.changeToOffset(0x0010115e);
                    // Address imgBase = plugin.program.getImageBase();
                    // Address addr = imgBase.getNewAddress(0x0010115e);
                    // plugin.unsafeGoTo(addr);
                    // plugin.console.println("going to address");
                }
            };
            action.setToolBarData(new ToolBarData(Icons.ADD_ICON, null));
            action.setEnabled(true);
            action.markHelpUnnecessary();
            dockingTool.addLocalAction(this, action);
        }

        @Override
        public JComponent getComponent() {
            return panel;
        }
    }
}


