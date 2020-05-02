namespace USB2CAN
{
    partial class Form1
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.buttonCanalOpen = new System.Windows.Forms.Button();
            this.buttonCanalClose = new System.Windows.Forms.Button();
            this.groupBoxchannelParameters = new System.Windows.Forms.GroupBox();
            this.comboBoxBaudRates = new System.Windows.Forms.ComboBox();
            this.labeldeviceSerial = new System.Windows.Forms.Label();
            this.label1 = new System.Windows.Forms.Label();
            this.textBoxSerialNumber = new System.Windows.Forms.TextBox();
            this.groupBoxconnectionOptions = new System.Windows.Forms.GroupBox();
            this.checkBox4 = new System.Windows.Forms.CheckBox();
            this.checkBox3 = new System.Windows.Forms.CheckBox();
            this.checkBox2 = new System.Windows.Forms.CheckBox();
            this.checkBox1 = new System.Windows.Forms.CheckBox();
            this.groupBoxMessage = new System.Windows.Forms.GroupBox();
            this.textBoxmessageId = new System.Windows.Forms.TextBox();
            this.labelmessageId = new System.Windows.Forms.Label();
            this.buttonSendMessage = new System.Windows.Forms.Button();
            this.groupBoxchannelParameters.SuspendLayout();
            this.groupBoxconnectionOptions.SuspendLayout();
            this.groupBoxMessage.SuspendLayout();
            this.SuspendLayout();
            // 
            // buttonCanalOpen
            // 
            this.buttonCanalOpen.Location = new System.Drawing.Point(41, 249);
            this.buttonCanalOpen.Name = "buttonCanalOpen";
            this.buttonCanalOpen.Size = new System.Drawing.Size(75, 23);
            this.buttonCanalOpen.TabIndex = 0;
            this.buttonCanalOpen.Text = "Open";
            this.buttonCanalOpen.UseVisualStyleBackColor = true;
            this.buttonCanalOpen.Click += new System.EventHandler(this.buttonCanalOpen_Click);
            // 
            // buttonCanalClose
            // 
            this.buttonCanalClose.Location = new System.Drawing.Point(165, 249);
            this.buttonCanalClose.Name = "buttonCanalClose";
            this.buttonCanalClose.Size = new System.Drawing.Size(75, 23);
            this.buttonCanalClose.TabIndex = 1;
            this.buttonCanalClose.Text = "Close";
            this.buttonCanalClose.UseVisualStyleBackColor = true;
            this.buttonCanalClose.Click += new System.EventHandler(this.buttonCanalClose_Click);
            // 
            // groupBoxchannelParameters
            // 
            this.groupBoxchannelParameters.Controls.Add(this.comboBoxBaudRates);
            this.groupBoxchannelParameters.Controls.Add(this.labeldeviceSerial);
            this.groupBoxchannelParameters.Controls.Add(this.label1);
            this.groupBoxchannelParameters.Controls.Add(this.textBoxSerialNumber);
            this.groupBoxchannelParameters.Controls.Add(this.groupBoxconnectionOptions);
            this.groupBoxchannelParameters.Controls.Add(this.buttonCanalOpen);
            this.groupBoxchannelParameters.Controls.Add(this.buttonCanalClose);
            this.groupBoxchannelParameters.Location = new System.Drawing.Point(12, 12);
            this.groupBoxchannelParameters.Name = "groupBoxchannelParameters";
            this.groupBoxchannelParameters.Size = new System.Drawing.Size(289, 305);
            this.groupBoxchannelParameters.TabIndex = 2;
            this.groupBoxchannelParameters.TabStop = false;
            this.groupBoxchannelParameters.Text = "Channel Parameters";
            // 
            // comboBoxBaudRates
            // 
            this.comboBoxBaudRates.FormattingEnabled = true;
            this.comboBoxBaudRates.Items.AddRange(new object[] {
            "Custom (Unavailable)",
            "1 MBit/sec",
            "800 kBit/s",
            "500 kBit/sec",
            "250 kBit/sec",
            "125 kBit/sec",
            "100 kBit/sec",
            "50 kBit/sec",
            "20 kBit/sec",
            "10 kBit/sec"});
            this.comboBoxBaudRates.Location = new System.Drawing.Point(142, 191);
            this.comboBoxBaudRates.Name = "comboBoxBaudRates";
            this.comboBoxBaudRates.Size = new System.Drawing.Size(121, 21);
            this.comboBoxBaudRates.TabIndex = 3;
            this.comboBoxBaudRates.SelectedIndexChanged += new System.EventHandler(this.comboBoxBaudRates_SelectedIndexChanged);
            // 
            // labeldeviceSerial
            // 
            this.labeldeviceSerial.AutoSize = true;
            this.labeldeviceSerial.Location = new System.Drawing.Point(32, 157);
            this.labeldeviceSerial.Name = "labeldeviceSerial";
            this.labeldeviceSerial.Size = new System.Drawing.Size(113, 13);
            this.labeldeviceSerial.TabIndex = 6;
            this.labeldeviceSerial.Text = "Device Serial Number:";
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(32, 194);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(64, 13);
            this.label1.TabIndex = 5;
            this.label1.Text = "Baud Rate: ";
            // 
            // textBoxSerialNumber
            // 
            this.textBoxSerialNumber.Location = new System.Drawing.Point(163, 154);
            this.textBoxSerialNumber.Name = "textBoxSerialNumber";
            this.textBoxSerialNumber.Size = new System.Drawing.Size(100, 20);
            this.textBoxSerialNumber.TabIndex = 4;
            this.textBoxSerialNumber.Text = "ED000200";
            this.textBoxSerialNumber.TextChanged += new System.EventHandler(this.textBoxSerialNumber_TextChanged);
            // 
            // groupBoxconnectionOptions
            // 
            this.groupBoxconnectionOptions.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.groupBoxconnectionOptions.Controls.Add(this.checkBox4);
            this.groupBoxconnectionOptions.Controls.Add(this.checkBox3);
            this.groupBoxconnectionOptions.Controls.Add(this.checkBox2);
            this.groupBoxconnectionOptions.Controls.Add(this.checkBox1);
            this.groupBoxconnectionOptions.Location = new System.Drawing.Point(6, 19);
            this.groupBoxconnectionOptions.Name = "groupBoxconnectionOptions";
            this.groupBoxconnectionOptions.Size = new System.Drawing.Size(277, 120);
            this.groupBoxconnectionOptions.TabIndex = 3;
            this.groupBoxconnectionOptions.TabStop = false;
            this.groupBoxconnectionOptions.Text = "Connection Options";
            // 
            // checkBox4
            // 
            this.checkBox4.AutoSize = true;
            this.checkBox4.Location = new System.Drawing.Point(29, 97);
            this.checkBox4.Name = "checkBox4";
            this.checkBox4.Size = new System.Drawing.Size(104, 17);
            this.checkBox4.TabIndex = 3;
            this.checkBox4.Text = "Loopback Mode";
            this.checkBox4.UseVisualStyleBackColor = true;
            // 
            // checkBox3
            // 
            this.checkBox3.AutoSize = true;
            this.checkBox3.Location = new System.Drawing.Point(29, 75);
            this.checkBox3.Name = "checkBox3";
            this.checkBox3.Size = new System.Drawing.Size(82, 17);
            this.checkBox3.TabIndex = 2;
            this.checkBox3.Text = "Silent Mode";
            this.checkBox3.UseVisualStyleBackColor = true;
            // 
            // checkBox2
            // 
            this.checkBox2.AutoSize = true;
            this.checkBox2.Location = new System.Drawing.Point(29, 52);
            this.checkBox2.Name = "checkBox2";
            this.checkBox2.Size = new System.Drawing.Size(160, 17);
            this.checkBox2.TabIndex = 1;
            this.checkBox2.Text = "Disable Auto Retransmission";
            this.checkBox2.UseVisualStyleBackColor = true;
            // 
            // checkBox1
            // 
            this.checkBox1.AutoSize = true;
            this.checkBox1.Location = new System.Drawing.Point(29, 31);
            this.checkBox1.Name = "checkBox1";
            this.checkBox1.Size = new System.Drawing.Size(138, 17);
            this.checkBox1.TabIndex = 0;
            this.checkBox1.Text = "Enable Status Message";
            this.checkBox1.UseVisualStyleBackColor = true;
            // 
            // groupBoxMessage
            // 
            this.groupBoxMessage.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.groupBoxMessage.Controls.Add(this.buttonSendMessage);
            this.groupBoxMessage.Controls.Add(this.labelmessageId);
            this.groupBoxMessage.Controls.Add(this.textBoxmessageId);
            this.groupBoxMessage.Location = new System.Drawing.Point(307, 12);
            this.groupBoxMessage.Name = "groupBoxMessage";
            this.groupBoxMessage.Size = new System.Drawing.Size(345, 305);
            this.groupBoxMessage.TabIndex = 3;
            this.groupBoxMessage.TabStop = false;
            this.groupBoxMessage.Text = "groupBox1";
            // 
            // textBoxmessageId
            // 
            this.textBoxmessageId.Location = new System.Drawing.Point(106, 31);
            this.textBoxmessageId.Name = "textBoxmessageId";
            this.textBoxmessageId.Size = new System.Drawing.Size(100, 20);
            this.textBoxmessageId.TabIndex = 5;
            this.textBoxmessageId.Text = "0x0";
            // 
            // labelmessageId
            // 
            this.labelmessageId.AutoSize = true;
            this.labelmessageId.Location = new System.Drawing.Point(23, 34);
            this.labelmessageId.Name = "labelmessageId";
            this.labelmessageId.Size = new System.Drawing.Size(67, 13);
            this.labelmessageId.TabIndex = 7;
            this.labelmessageId.Text = "Message ID:";
            // 
            // buttonSendMessage
            // 
            this.buttonSendMessage.Location = new System.Drawing.Point(26, 175);
            this.buttonSendMessage.Name = "buttonSendMessage";
            this.buttonSendMessage.Size = new System.Drawing.Size(75, 23);
            this.buttonSendMessage.TabIndex = 8;
            this.buttonSendMessage.Text = "Send Message";
            this.buttonSendMessage.UseVisualStyleBackColor = true;
            this.buttonSendMessage.Click += new System.EventHandler(this.buttonSendMessage_Click);
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(664, 450);
            this.Controls.Add(this.groupBoxMessage);
            this.Controls.Add(this.groupBoxchannelParameters);
            this.Name = "Form1";
            this.Text = "Form1";
            this.groupBoxchannelParameters.ResumeLayout(false);
            this.groupBoxchannelParameters.PerformLayout();
            this.groupBoxconnectionOptions.ResumeLayout(false);
            this.groupBoxconnectionOptions.PerformLayout();
            this.groupBoxMessage.ResumeLayout(false);
            this.groupBoxMessage.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button buttonCanalOpen;
        private System.Windows.Forms.Button buttonCanalClose;
        private System.Windows.Forms.GroupBox groupBoxchannelParameters;
        private System.Windows.Forms.Label labeldeviceSerial;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.TextBox textBoxSerialNumber;
        private System.Windows.Forms.GroupBox groupBoxconnectionOptions;
        private System.Windows.Forms.ComboBox comboBoxBaudRates;
        private System.Windows.Forms.CheckBox checkBox4;
        private System.Windows.Forms.CheckBox checkBox3;
        private System.Windows.Forms.CheckBox checkBox2;
        private System.Windows.Forms.CheckBox checkBox1;
        private System.Windows.Forms.GroupBox groupBoxMessage;
        private System.Windows.Forms.Label labelmessageId;
        private System.Windows.Forms.TextBox textBoxmessageId;
        private System.Windows.Forms.Button buttonSendMessage;
    }
}

