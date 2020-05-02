using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using CanalWrapper;

namespace USB2CAN
{



    public partial class Form1 : Form
    {   

        public Form1()
        {
            InitializeComponent();

            InitializeCanalComponents();
        }


        long CanalHandle;
        string CanalBaudRate;
        string SerialNumber;
        long CanalConnectionFlags;


        private void InitializeCanalComponents()
        {
            SerialNumber = textBoxSerialNumber.Text;

            comboBoxBaudRates.SelectedIndex = 4;
        }


        private void buttonCanalOpen_Click(object sender, EventArgs e)
        {

            string connection_string = SerialNumber + " ; " + CanalBaudRate;

            Console.WriteLine("Connecting: \"" + connection_string + "\"");

            if ((CanalHandle = Canal.canwrap_CanalOpen(connection_string, CanalConnectionFlags)) <= 0)
            {
                Console.WriteLine("Failed to open CAN Line; Handle: " + CanalHandle);
            }
            else
            {
                Console.WriteLine("Succesfully opened CAN Line; Handle: " + CanalHandle);
            }
        }

        private void buttonCanalClose_Click(object sender, EventArgs e)
        {
            int code;
            code = Canal.canwrap_CanalClose(CanalHandle);
            if (Canal.error_codes.ContainsKey(code))
            {
                Console.WriteLine(Canal.error_codes[code]);
            }
            else
            {
                Console.WriteLine("Unknown Error Code");
            }
        }

        private void comboBoxBaudRates_SelectedIndexChanged(object sender, EventArgs e)
        {
            // Saves the current selected baudrate register code
            //
            if (Canal.baudrates.ContainsKey(comboBoxBaudRates.SelectedIndex))
            {
                CanalBaudRate = Canal.baudrates[comboBoxBaudRates.SelectedIndex];
            }
            else
            {
                Console.WriteLine("Invalid Baud Rate");
            }

            
        }

        private void textBoxSerialNumber_TextChanged(object sender, EventArgs e)
        {
            SerialNumber = textBoxSerialNumber.Text;
        }

        private void buttonSendMessage_Click(object sender, EventArgs e)
        {
            CanalMsg msg = new CanalMsg();
            msg.data = new byte[8];
            msg.id = 0x120;
            msg.sizeData = 8;
            msg.data[0] = 0xA5;

            


            int code;
            code = Canal.canalBlockingSend(CanalHandle, msg, 100);
            if (Canal.error_codes.ContainsKey(code))
            {
                Console.WriteLine(Canal.error_codes[code]);
            }
            else
            {
                Console.WriteLine("Unknown Error Code");
            }

        }
    }
}
